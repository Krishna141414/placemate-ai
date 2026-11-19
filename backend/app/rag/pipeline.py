"""The question-answering pipeline.

`run_pipeline` is a generator. It yields an event after each stage, so the
same code drives the streaming UI, the JSON endpoint, the tests and the
evaluation. `answer_question` simply runs it to the end.

final mode:    input guard -> hybrid retrieval -> rerank -> grounding check
               -> generation -> output guard
baseline mode: vector retrieval -> generation   (no guards, no reranking)
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import get_settings
from app.llm import router
from app.llm.base import LLMRequest, Passage, ProviderError
from app.rag.prompts import NOT_IN_DOCUMENTS, SYSTEM_PROMPT, build_prompt
from app.rag.retriever import Mode, RetrievalResult, ScoredChunk, retrieve
from app.security.injection import CANARY, filter_output, scan_user_input

logger = logging.getLogger("placemate.pipeline")

REFUSAL_MESSAGE = (
    "I could not find this in the placement documents, so I will not guess. "
    "Try rephrasing the question, or ask your placement coordinator."
)
BLOCKED_MESSAGE = (
    "This message looks like an attempt to change how PlaceMate works, so it was not processed. "
    "Please ask a placement question instead."
)
SNIPPET_CHARS = 320
_RAW_CITATION_RE = re.compile(r"\[(\d{1,3})\]")


@dataclass
class Step:
    name: str
    label: str
    status: str  # done | skipped | blocked | refused | fallback
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class AnswerResult:
    question: str
    answer: str
    mode: str
    citations: list[int] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    refused: bool = False
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    provider: str = "none"
    model: str = ""
    fallbacks: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    top_score: float | None = None
    retrieved_doc_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _snippet(text: str) -> str:
    text = " ".join(text.replace("...", " ").split())
    if len(text) <= SNIPPET_CHARS:
        return text
    cut = text[:SNIPPET_CHARS].rsplit(" ", 1)[0]
    return f"{cut}..."


def _source_cards(results: list[ScoredChunk]) -> list[dict[str, Any]]:
    return [
        {
            "n": n,
            "doc_key": item.chunk.doc_key,
            "title": item.chunk.title,
            "doc_type": item.chunk.doc_type,
            "section": item.chunk.section,
            "snippet": _snippet(item.chunk.text),
            "text": item.chunk.text,
            "score": round(float(item.score), 3),
        }
        for n, item in enumerate(results, start=1)
    ]


def _passages(results: list[ScoredChunk]) -> list[Passage]:
    return [
        Passage(n=n, title=item.chunk.title, section=item.chunk.section, text=item.chunk.text, score=float(item.score))
        for n, item in enumerate(results, start=1)
    ]


def _words(text: str, group: int = 3) -> Iterator[str]:
    """Split text into small pieces for streaming, keeping whitespace."""
    tokens = re.findall(r"\S+\s*", text)
    for i in range(0, len(tokens), group):
        yield "".join(tokens[i : i + group])


def _step_event(step: Step) -> dict[str, Any]:
    return {"type": "step", "step": asdict(step)}


def run_pipeline(question: str, *, mode: Mode = "final") -> Iterator[dict[str, Any]]:
    settings = get_settings()
    started = time.perf_counter()
    guarded = mode == "final"
    steps: list[Step] = []
    result = AnswerResult(question=question, answer="", mode=mode)

    def add(step: Step) -> dict[str, Any]:
        steps.append(step)
        return _step_event(step)

    def finish() -> dict[str, Any]:
        result.steps = [asdict(step) for step in steps]
        result.latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {"type": "final", "result": result.to_dict()}

    # 1. Input guard ------------------------------------------------------
    if guarded:
        t = time.perf_counter()
        guard = scan_user_input(question)
        duration = (time.perf_counter() - t) * 1000
        if guard.blocked:
            yield add(Step("guard", "Input guard", "blocked", "Blocked: " + "; ".join(guard.labels) + ".", duration))
            result.blocked = True
            result.block_reasons = guard.labels
            result.answer = BLOCKED_MESSAGE
            yield from ({"type": "delta", "text": piece} for piece in _words(result.answer))
            yield finish()
            return
        yield add(Step("guard", "Input guard", "done", "No injection patterns found.", duration))
    else:
        yield add(Step("guard", "Input guard", "skipped", "Not part of the baseline."))

    # 2. Retrieve (and 3. rerank) ----------------------------------------
    retrieval: RetrievalResult = retrieve(question, mode=mode)
    timings = retrieval.timings
    if guarded:
        counts = retrieval.counts
        yield add(
            Step(
                "retrieve",
                "Hybrid retrieval",
                "done",
                f"BM25 found {counts.get('bm25', 0)}, vectors found {counts.get('vector', 0)}; "
                f"fused to {counts.get('fused', 0)} candidates with RRF.",
                timings.get("vector_ms", 0) + timings.get("bm25_ms", 0),
            )
        )
        # Retrieved text is scanned again here, in case a document reached
        # the index without passing through the ingest sanitiser.
        safe = [item for item in retrieval.results if not scan_user_input(item.chunk.text).blocked]
        dropped = len(retrieval.results) - len(safe)
        results = safe
        best = f"{results[0].score:.2f}" if results else "n/a"
        detail = f"Cross-encoder kept the top {len(results)}; best score {best}."
        if dropped:
            detail += f" Dropped {dropped} passage(s) containing instruction-like text."
        yield add(Step("rerank", "Rerank", "done", detail, timings.get("rerank_ms", 0)))
    else:
        results = retrieval.results
        yield add(
            Step("retrieve", "Vector retrieval", "done", f"Top {len(results)} by cosine similarity.", timings.get("vector_ms", 0))
        )
        yield add(Step("rerank", "Rerank", "skipped", "Not part of the baseline."))

    result.sources = _source_cards(results)
    result.top_score = round(float(results[0].score), 3) if results else None
    result.retrieved_doc_keys = [item.chunk.doc_key for item in results]
    yield {"type": "sources", "sources": result.sources}

    # 4. Grounding check --------------------------------------------------
    if guarded:
        threshold = settings.rerank_refusal_threshold
        if not results or results[0].score < threshold:
            best = f"{results[0].score:.2f}" if results else "none"
            yield add(
                Step(
                    "grounding",
                    "Grounding check",
                    "refused",
                    f"Best passage score {best} is below the threshold {threshold:.2f}. No model was called.",
                )
            )
            result.refused = True
            result.answer = REFUSAL_MESSAGE
            yield from ({"type": "delta", "text": piece} for piece in _words(result.answer))
            yield finish()
            return
        yield add(
            Step(
                "grounding",
                "Grounding check",
                "done",
                f"Best passage score {results[0].score:.2f} is above the threshold {threshold:.2f}.",
            )
        )
    else:
        yield add(Step("grounding", "Grounding check", "skipped", "Not part of the baseline."))

    if not results:  # baseline with an empty index
        result.refused = True
        result.answer = REFUSAL_MESSAGE
        yield finish()
        return

    # 5. Generate ---------------------------------------------------------
    passages = _passages(results)
    request = LLMRequest(
        system=SYSTEM_PROMPT,
        prompt=build_prompt(question, passages),
        question=question,
        passages=passages,
        max_tokens=settings.llm_max_output_tokens,
    )
    allowed_text = "\n".join(passage.text for passage in passages)

    def accept(text: str) -> str | None:
        """Reject an answer that leaks the prompt or cites nothing."""
        if CANARY in text:
            return "leaked the system prompt"
        if NOT_IN_DOCUMENTS in text:
            return None
        _, citations, _ = filter_output(text, len(passages), allowed_text)
        if not citations:
            return "answer had no valid citation"
        return None

    t = time.perf_counter()
    try:
        llm = router.generate(request, accept=accept if guarded else None)
    except ProviderError:
        logger.exception("all_providers_failed")
        yield add(Step("generate", "Generate", "refused", "No provider could answer.", (time.perf_counter() - t) * 1000))
        result.refused = True
        result.answer = REFUSAL_MESSAGE
        yield finish()
        return

    result.provider, result.model, result.fallbacks = llm.provider, llm.model, llm.fallbacks
    detail = f"Answered by {llm.provider} ({llm.model})."
    if llm.fallbacks:
        detail += " Fell back after: " + "; ".join(llm.fallbacks) + "."
    yield add(Step("generate", "Generate", "fallback" if llm.fallbacks else "done", detail, (time.perf_counter() - t) * 1000))

    # 6. Output guard -----------------------------------------------------
    text = llm.text.strip()
    if NOT_IN_DOCUMENTS in text:
        result.refused = True
        result.answer = REFUSAL_MESSAGE
        yield add(Step("output_guard", "Output guard", "refused", "The model reported that the sources do not contain the answer."))
    elif guarded:
        cleaned, citations, notes = filter_output(text, len(passages), allowed_text)
        if not cleaned:
            result.refused = True
            result.answer = REFUSAL_MESSAGE
            yield add(Step("output_guard", "Output guard", "refused", "Answer discarded: " + ", ".join(notes) + "."))
        else:
            result.answer, result.citations = cleaned, citations
            detail = "Citations checked against the sources."
            detail += " " + "; ".join(note.capitalize() for note in notes) + "." if notes else " Nothing removed."
            yield add(Step("output_guard", "Output guard", "done", detail))
    else:
        # Baseline: the raw answer, with whatever citation numbers it contains.
        result.answer = text
        result.citations = list(dict.fromkeys(int(n) for n in _RAW_CITATION_RE.findall(text)))
        yield add(Step("output_guard", "Output guard", "skipped", "Not part of the baseline."))

    yield from ({"type": "delta", "text": piece} for piece in _words(result.answer))
    yield finish()


def answer_question(question: str, *, mode: Mode = "final") -> AnswerResult:
    final: dict[str, Any] = {}
    for event in run_pipeline(question, mode=mode):
        if event["type"] == "final":
            final = event["result"]
    return AnswerResult(**final)
