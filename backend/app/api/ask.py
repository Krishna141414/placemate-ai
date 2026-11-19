"""Ask PlaceMate: JSON and streaming (SSE) endpoints, and saved conversations."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.errors import AppError
from app.models import Conversation, Message, User
from app.rag.pipeline import run_pipeline
from app.schemas import AnswerOut, AskRequest, ConversationOut, ConversationSummary, MessageOut
from app.security.auth import get_current_user
from app.security.pii import scrub_for_log
from app.services import events

logger = logging.getLogger("placemate.ask")
router = APIRouter(prefix="/api", tags=["ask"])

SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def _check_conversation(db: Session, user: User, conversation_id: int | None) -> None:
    if conversation_id is None:
        return
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise AppError(404, "conversation_not_found", "That conversation does not exist.")


def _persist(db: Session, user_id: int, body: AskRequest, result: dict[str, Any]) -> tuple[int, int]:
    """Save the question and answer, and log an analytics event."""
    conversation = db.get(Conversation, body.conversation_id) if body.conversation_id else None
    if conversation is None:
        title = " ".join(body.question.split())[:80]
        conversation = Conversation(user_id=user_id, title=title)
        db.add(conversation)
        db.flush()

    db.add(Message(conversation_id=conversation.id, role="user", content=body.question, meta={}))
    meta = {key: result[key] for key in (
        "citations", "sources", "refused", "blocked", "block_reasons", "provider", "model",
        "fallbacks", "steps", "latency_ms", "mode",
    )}
    answer = Message(conversation_id=conversation.id, role="assistant", content=result["answer"], meta=meta)
    db.add(answer)
    conversation.updated_at = func.now()
    db.commit()

    event_type = events.ASK_BLOCKED if result["blocked"] else events.ASK_REFUSED if result["refused"] else events.ASK
    top_source = result["sources"][0] if result["sources"] else None
    events.log_event(
        db,
        event_type,
        user_id,
        question=scrub_for_log(" ".join(body.question.split()))[:300],
        provider=result["provider"],
        mode=result["mode"],
        latency_ms=result["latency_ms"],
        top_doc=top_source["doc_key"] if top_source else None,
        top_title=top_source["title"] if top_source else None,
        reasons=result["block_reasons"],
    )
    return conversation.id, answer.id


@router.post("/ask", response_model=AnswerOut, summary="Ask a question and get a cited answer")
def ask(body: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AnswerOut:
    _check_conversation(db, user, body.conversation_id)
    result: dict[str, Any] = {}
    for event in run_pipeline(body.question, mode=body.mode):
        if event["type"] == "final":
            result = event["result"]
    conversation_id, message_id = _persist(db, user.id, body, result)
    return AnswerOut(conversation_id=conversation_id, message_id=message_id, **result)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream(body: AskRequest, user_id: int) -> Iterator[str]:
    try:
        for event in run_pipeline(body.question, mode=body.mode):
            kind = event["type"]
            if kind == "step":
                yield _sse("step", event["step"])
            elif kind == "sources":
                yield _sse("sources", {"sources": event["sources"]})
            elif kind == "delta":
                yield _sse("delta", {"text": event["text"]})
            elif kind == "final":
                result = event["result"]
                # The request's session is closed by the time a streamed body
                # is produced, so the stream uses its own.
                with SessionLocal() as db:
                    conversation_id, message_id = _persist(db, user_id, body, result)
                yield _sse("final", {"conversation_id": conversation_id, "message_id": message_id, **result})
    except Exception:
        logger.exception("ask_stream_failed")
        yield _sse("error", {"code": "internal_error", "message": "Something went wrong while answering. Please try again."})


@router.post("/ask/stream", summary="Ask a question; the answer arrives as server-sent events")
def ask_stream(
    body: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> StreamingResponse:
    _check_conversation(db, user, body.conversation_id)
    return StreamingResponse(_stream(body, user.id), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/conversations", response_model=list[ConversationSummary], summary="The user's saved conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ConversationSummary]:
    rows = (
        db.query(Conversation, func.count(Message.id))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(50)
        .all()
    )
    return [
        ConversationSummary(id=c.id, title=c.title, updated_at=c.updated_at, message_count=count) for c, count in rows
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut, summary="One conversation with its messages")
def get_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ConversationOut:
    conversation = db.get(Conversation, conversation_id)
    # A conversation that belongs to someone else is reported as missing.
    if conversation is None or conversation.user_id != user.id:
        raise AppError(404, "conversation_not_found", "That conversation does not exist.")
    return ConversationOut(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageOut(id=m.id, role=m.role, content=m.content, meta=m.meta or {}, created_at=m.created_at)
            for m in conversation.messages
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=204, summary="Delete one of the user's conversations")
def delete_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise AppError(404, "conversation_not_found", "That conversation does not exist.")
    db.delete(conversation)
    db.commit()
