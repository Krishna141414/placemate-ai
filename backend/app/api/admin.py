"""Coordinator routes. Every route here requires the coordinator role."""

from __future__ import annotations

import hashlib
import logging
import time

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError
from app.models import Document, Event, User
from app.rag.index import IndexStore
from app.rag.loader import build_source_doc
from app.schemas import DocumentOut, EventOut, ReindexOut, UploadOut
from app.security.auth import require_coordinator
from app.security.uploads import read_limited, sanitize_filename, validate_bytes
from app.services import analytics, events

logger = logging.getLogger("placemate.admin")
router = APIRouter(prefix="/api/admin", tags=["coordinator"], dependencies=[Depends(require_coordinator)])


def _reindex(db: Session) -> ReindexOut:
    started = time.perf_counter()
    store = IndexStore.build(db)
    return ReindexOut(documents=store.document_count, chunks=len(store), duration_ms=round((time.perf_counter() - started) * 1000, 1))


@router.get("/documents", response_model=list[DocumentOut], summary="Every indexed document")
def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    rows = db.query(Document).order_by(Document.source.desc(), Document.doc_type, Document.title).all()
    return [DocumentOut.model_validate(row) for row in rows]


@router.post("/documents", response_model=UploadOut, status_code=201, summary="Upload a .md, .txt or .pdf document and re-index")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(require_coordinator),
    db: Session = Depends(get_db),
) -> UploadOut:
    settings = get_settings()
    filename = file.filename or "document"
    try:
        data = await read_limited(file, settings.max_upload_mb * 1024 * 1024)
        upload = validate_bytes(filename, data)
    except AppError as exc:
        events.log_event(db, events.UPLOAD_REJECTED, user.id, filename=sanitize_filename(filename), code=exc.code)
        raise

    checksum = hashlib.sha256(upload.data).hexdigest()
    duplicate = db.query(Document).filter(Document.checksum == checksum).first()
    if duplicate is not None:
        events.log_event(db, events.UPLOAD_REJECTED, user.id, filename=upload.safe_name, code="duplicate")
        raise AppError(409, "duplicate", f'This file is already indexed as "{duplicate.title}".')

    path = settings.upload_dir / upload.stored_name
    path.write_bytes(upload.data)
    stem = upload.stored_name.rsplit(".", 1)[0]
    source = build_source_doc(
        upload.text,
        filename=upload.stored_name,
        path=str(path),
        source="upload",
        size_bytes=len(upload.data),
        checksum=checksum,
        doc_key=f"upload-{stem}",
    )
    document = Document(
        doc_key=source.doc_key,
        title=source.title,
        doc_type=source.doc_type,
        company_id=source.company_id,
        source="upload",
        filename=upload.stored_name,
        path=str(path),
        checksum=checksum,
        size_bytes=len(upload.data),
        removed_lines=len(source.removed_lines),
        uploaded_by=user.id,
    )
    db.add(document)
    db.commit()

    try:
        reindex = _reindex(db)
    except Exception:
        # Roll the upload back so the index and the table stay consistent.
        logger.exception("reindex_after_upload_failed")
        db.delete(document)
        db.commit()
        path.unlink(missing_ok=True)
        raise AppError(500, "reindex_failed", "The file was valid but could not be indexed. It was not added.")

    db.refresh(document)
    events.log_event(
        db, events.UPLOAD, user.id, filename=upload.safe_name, title=document.title, chunks=document.chunk_count,
        removed_lines=len(source.removed_lines),
    )
    return UploadOut(document=DocumentOut.model_validate(document), reindex=reindex, removed_lines=source.removed_lines)


@router.delete("/documents/{document_id}", response_model=ReindexOut, summary="Delete an uploaded document and re-index")
def delete_document(document_id: int, user: User = Depends(require_coordinator), db: Session = Depends(get_db)) -> ReindexOut:
    document = db.get(Document, document_id)
    if document is None:
        raise AppError(404, "document_not_found", "That document does not exist.")
    if document.source != "upload":
        raise AppError(409, "seed_document", "Sample documents are part of the repository and cannot be deleted here.")
    title = document.title
    get_settings().upload_dir.joinpath(document.filename).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
    result = _reindex(db)
    events.log_event(db, events.DOCUMENT_DELETED, user.id, title=title)
    return result


@router.post("/reindex", response_model=ReindexOut, summary="Rebuild the search index from all documents")
def reindex(user: User = Depends(require_coordinator), db: Session = Depends(get_db)) -> ReindexOut:
    result = _reindex(db)
    events.log_event(db, events.REINDEX, user.id, chunks=result.chunks, documents=result.documents)
    return result


@router.get("/analytics", summary="Questions, unanswered questions, eligibility and provider usage")
def get_analytics(db: Session = Depends(get_db)) -> dict:
    return analytics.summary(db)


@router.get("/logs", response_model=list[EventOut], summary="Recent activity as readable rows")
def logs(
    type: str | None = Query(default=None, max_length=40, pattern=r"^[a-z_]+$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    query = db.query(Event, User.email).outerjoin(User, User.id == Event.user_id)
    if type:
        query = query.filter(Event.type == type)
    rows = query.order_by(Event.id.desc()).limit(limit).all()
    return [
        EventOut(id=event.id, type=event.type, user=email, summary=analytics.describe_event(event, email), created_at=event.created_at)
        for event, email in rows
    ]
