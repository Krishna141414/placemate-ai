"""Retrieval.

`baseline`: vector search only, top k straight from FAISS.
`final`:    BM25 and vector candidates, fused with Reciprocal Rank Fusion,
            then reranked by a cross-encoder.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from app.config import get_settings
from app.rag.chunker import Chunk
from app.rag.index import IndexStore, get_index
from app.rag.models import rerank_scores

Mode = Literal["baseline", "final"]


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float  # the score that decided the final order
    vector_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None
    vector_rank: int | None = None
    bm25_rank: int | None = None


@dataclass
class RetrievalResult:
    mode: str
    results: list[ScoredChunk]
    candidates: list[ScoredChunk]  # fused list before reranking (final mode)
    timings: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def top_score(self) -> float | None:
        return self.results[0].score if self.results else None


def rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: score(d) = sum over lists of 1 / (k + rank)."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


def _allowed(chunk: Chunk, company_id: str | None, doc_types: list[str] | None) -> bool:
    if company_id and chunk.company_id != company_id:
        return False
    if doc_types and chunk.doc_type not in doc_types:
        return False
    return True


def retrieve(
    query: str,
    *,
    mode: Mode = "final",
    top_k: int | None = None,
    company_id: str | None = None,
    doc_types: list[str] | None = None,
    index: IndexStore | None = None,
) -> RetrievalResult:
    settings = get_settings()
    index = index or get_index()
    top_k = top_k or settings.top_k
    filtered = bool(company_id or doc_types)
    # With a filter the whole index is scored, then filtered. It is small.
    pool = len(index) if filtered else settings.retrieve_candidates
    timings: dict[str, float] = {}

    started = time.perf_counter()
    vector_hits = [
        (i, s) for i, s in index.vector_search(query, pool) if _allowed(index.chunks[i], company_id, doc_types)
    ][: settings.retrieve_candidates]
    timings["vector_ms"] = (time.perf_counter() - started) * 1000
    vector_rank = {i: rank for rank, (i, _) in enumerate(vector_hits, start=1)}
    vector_score = dict(vector_hits)

    if mode == "baseline":
        results = [
            ScoredChunk(chunk=index.chunks[i], score=s, vector_score=s, vector_rank=vector_rank[i])
            for i, s in vector_hits[:top_k]
        ]
        return RetrievalResult(
            mode=mode, results=results, candidates=results, timings=timings, counts={"vector": len(vector_hits)}
        )

    started = time.perf_counter()
    bm25_hits = [
        (i, s) for i, s in index.bm25_search(query, pool) if _allowed(index.chunks[i], company_id, doc_types)
    ][: settings.retrieve_candidates]
    timings["bm25_ms"] = (time.perf_counter() - started) * 1000
    bm25_rank = {i: rank for rank, (i, _) in enumerate(bm25_hits, start=1)}
    bm25_score = dict(bm25_hits)

    fused = rrf_fuse([[i for i, _ in vector_hits], [i for i, _ in bm25_hits]], k=settings.rrf_k)
    fused = fused[: settings.retrieve_candidates]
    candidates = [
        ScoredChunk(
            chunk=index.chunks[i],
            score=score,
            rrf_score=score,
            vector_score=vector_score.get(i),
            bm25_score=bm25_score.get(i),
            vector_rank=vector_rank.get(i),
            bm25_rank=bm25_rank.get(i),
        )
        for i, score in fused
    ]

    started = time.perf_counter()
    scores = rerank_scores(query, [candidate.chunk.index_text for candidate in candidates])
    timings["rerank_ms"] = (time.perf_counter() - started) * 1000
    reranked = []
    for candidate, score in zip(candidates, scores):
        reranked.append(
            ScoredChunk(
                chunk=candidate.chunk,
                score=score,
                rerank_score=score,
                rrf_score=candidate.rrf_score,
                vector_score=candidate.vector_score,
                bm25_score=candidate.bm25_score,
                vector_rank=candidate.vector_rank,
                bm25_rank=candidate.bm25_rank,
            )
        )
    reranked.sort(key=lambda item: -item.score)

    return RetrievalResult(
        mode=mode,
        results=reranked[:top_k],
        candidates=candidates,
        timings=timings,
        counts={"vector": len(vector_hits), "bm25": len(bm25_hits), "fused": len(candidates)},
    )
