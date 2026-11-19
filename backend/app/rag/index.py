"""The search index: FAISS for vectors, BM25 for keywords.

Chunks and embeddings are saved under `storage/index/`. A manifest records a
fingerprint of the corpus, so the index is reused when nothing changed and
rebuilt when a document was added, edited or removed. The FAISS and BM25
structures are rebuilt in memory from the saved arrays, which takes
milliseconds at this size.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document
from app.rag.chunker import CHUNKER_VERSION, Chunk, chunk_document
from app.rag.loader import SourceDoc, load_corpus
from app.rag.models import embed

logger = logging.getLogger("placemate.index")

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[+#.][a-z0-9+#]+)*|[a-z]\+\+|c#")
_STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from had has have how i if in is it its me my of on or our "
    "so than that the their them then there these they this to was we were what when where which who why will "
    "with would you your about into am any been being did not no should could".split()
)

_lock = threading.Lock()
_current: "IndexStore | None" = None


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens for BM25. Keeps terms like `c++` and `7.5`."""
    tokens = []
    for token in _TOKEN_RE.findall(text.lower()):
        token = token.strip(".")
        if not token or token in _STOPWORDS:
            continue
        # Light plural folding so "backlogs" matches "backlog".
        if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tokens


def corpus_fingerprint(docs: list[SourceDoc]) -> str:
    settings = get_settings()
    digest = hashlib.sha256()
    digest.update(f"{settings.embedding_model}|{CHUNKER_VERSION}".encode())
    for doc in sorted(docs, key=lambda d: d.doc_key):
        digest.update(f"{doc.doc_key}:{doc.checksum}".encode())
    return digest.hexdigest()


class IndexStore:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, fingerprint: str) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.fingerprint = fingerprint

        dim = embeddings.shape[1] if embeddings.size else 384
        self.faiss_index = faiss.IndexFlatIP(dim)
        if len(chunks):
            self.faiss_index.add(embeddings)
        self.bm25 = BM25Okapi([tokenize(chunk.index_text) or ["_"] for chunk in chunks]) if chunks else None

    def __len__(self) -> int:
        return len(self.chunks)

    @property
    def document_count(self) -> int:
        return len({chunk.doc_key for chunk in self.chunks})

    # --- search ---------------------------------------------------------

    def vector_search(self, query: str, k: int) -> list[tuple[int, float]]:
        if not self.chunks:
            return []
        scores, ids = self.faiss_index.search(embed([query]), min(k, len(self.chunks)))
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]

    def bm25_search(self, query: str, k: int) -> list[tuple[int, float]]:
        if not self.chunks or self.bm25 is None:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        order = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]

    # --- persistence ----------------------------------------------------

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "chunks.json").write_text(
            json.dumps([chunk.to_dict() for chunk in self.chunks], ensure_ascii=False), encoding="utf-8"
        )
        np.save(directory / "embeddings.npy", self.embeddings)
        (directory / "manifest.json").write_text(
            json.dumps({"fingerprint": self.fingerprint, "chunks": len(self.chunks), "built_at": time.time()}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: Path) -> "IndexStore | None":
        try:
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            chunks = [Chunk(**row) for row in json.loads((directory / "chunks.json").read_text(encoding="utf-8"))]
            embeddings = np.load(directory / "embeddings.npy")
        except (OSError, ValueError, TypeError, KeyError):
            return None
        if len(chunks) != embeddings.shape[0] or len(chunks) != manifest.get("chunks"):
            return None
        return cls(chunks, np.asarray(embeddings, dtype="float32"), manifest.get("fingerprint", ""))

    # --- lifecycle ------------------------------------------------------

    @staticmethod
    def _load_docs(db: Session) -> list[SourceDoc]:
        settings = get_settings()
        uploads = [
            (document.doc_key, Path(document.path))
            for document in db.query(Document).filter(Document.source == "upload").order_by(Document.id)
        ]
        return load_corpus(settings.data_dir, uploads)

    @classmethod
    def build(cls, db: Session) -> "IndexStore":
        """Read the corpus, chunk, embed, save, and make it the live index."""
        started = time.perf_counter()
        docs = cls._load_docs(db)
        per_doc = {doc.doc_key: chunk_document(doc) for doc in docs}
        chunks = [chunk for doc in docs for chunk in per_doc[doc.doc_key]]
        embeddings = embed([chunk.index_text for chunk in chunks])
        store = cls(chunks, embeddings, corpus_fingerprint(docs))
        store.save(get_settings().index_dir)
        _sync_documents(db, docs, {key: len(value) for key, value in per_doc.items()})
        set_index(store)
        logger.info(
            "index_built",
            extra={
                "documents": len(docs),
                "chunks": len(chunks),
                "seconds": round(time.perf_counter() - started, 2),
            },
        )
        return store

    @classmethod
    def ensure(cls, db: Session) -> "IndexStore":
        """Reuse the saved index if it matches the corpus, otherwise rebuild."""
        docs = cls._load_docs(db)
        saved = cls.load(get_settings().index_dir)
        if saved is not None and saved.fingerprint == corpus_fingerprint(docs):
            per_doc: dict[str, int] = {}
            for chunk in saved.chunks:
                per_doc[chunk.doc_key] = per_doc.get(chunk.doc_key, 0) + 1
            _sync_documents(db, docs, per_doc)
            set_index(saved)
            logger.info("index_loaded", extra={"chunks": len(saved)})
            return saved
        return cls.build(db)


def _sync_documents(db: Session, docs: list[SourceDoc], chunk_counts: dict[str, int]) -> None:
    """Keep the `documents` table in step with what is indexed."""
    existing = {document.doc_key: document for document in db.query(Document).all()}
    seed_keys = set()
    for doc in docs:
        row = existing.get(doc.doc_key)
        if doc.source == "seed":
            seed_keys.add(doc.doc_key)
        if row is None:
            row = Document(doc_key=doc.doc_key, source=doc.source, filename=doc.filename, path=doc.path)
            db.add(row)
        row.title = doc.title
        row.doc_type = doc.doc_type
        row.company_id = doc.company_id
        row.checksum = doc.checksum
        row.size_bytes = doc.size_bytes
        row.chunk_count = chunk_counts.get(doc.doc_key, 0)
        row.removed_lines = len(doc.removed_lines)
        if doc.source == "seed":
            row.filename = doc.filename
            row.path = doc.path
    # A seed file deleted from disk should not linger in the table.
    for key, row in existing.items():
        if row.source == "seed" and key not in seed_keys:
            db.delete(row)
    db.commit()


def set_index(store: IndexStore) -> None:
    global _current
    with _lock:
        _current = store


def get_index() -> IndexStore:
    """The live index. Built on first use if startup did not do it."""
    if _current is None:
        from app.db import SessionLocal

        with SessionLocal() as db:
            return IndexStore.ensure(db)
    return _current
