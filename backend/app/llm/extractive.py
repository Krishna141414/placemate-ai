"""Extractive provider: no generation at all.

It picks the sentences from the retrieved passages that best answer the
question and returns them with their citation numbers. Every word comes from
a source, so it cannot hallucinate, and it needs no key and no large model.
It is the last link in the fallback chain, which is why the app always
answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.llm.base import LLMRequest, Passage, ProviderError

MAX_UNITS = 6
MAX_WORDS = 130
MAX_PASSAGES = 3
# Only passages scoring within this margin of the best passage are used, so
# a neighbouring document (another company's rules) is not quoted by mistake.
PASSAGE_MARGIN = 3.0
# Sentences scoring within this margin of the best sentence are kept.
UNIT_MARGIN = 3.0
MIN_WORDS = 3
LONG_ITEM_WORDS = 45

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(*])")
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_MARKUP_RE = re.compile(r"\*\*|__|`")


@dataclass
class Unit:
    passage: Passage
    position: int
    text: str
    is_item: bool
    score: float = 0.0


def split_units(passage: Passage) -> list[Unit]:
    """Sentences of prose, and whole list items (a list item is one fact)."""
    units: list[Unit] = []
    for line in passage.text.split("\n"):
        is_item = bool(_BULLET_RE.match(line))
        line = _MARKUP_RE.sub("", _BULLET_RE.sub("", line)).strip()
        if not line or line.startswith("..."):
            continue
        if is_item and len(line.split()) <= LONG_ITEM_WORDS:
            pieces = [line]
        else:
            pieces = [piece.strip() for piece in _SENTENCE_SPLIT_RE.split(line)]
        for piece in pieces:
            if len(piece.split()) >= MIN_WORDS:
                units.append(Unit(passage=passage, position=len(units), text=piece, is_item=is_item))
    return units


def split_sentences(text: str) -> list[str]:
    return [unit.text for unit in split_units(Passage(n=1, title="", section="", text=text))]


class ExtractiveProvider:
    name = "extractive"
    model = "sentence-selection"

    def available(self) -> tuple[bool, str]:
        return True, ""

    def generate(self, request: LLMRequest) -> str:
        from app.rag.models import rerank_scores

        passages = request.passages[:MAX_PASSAGES]
        scored = [p for p in passages if p.score is not None]
        if scored:
            best_passage = max(p.score for p in scored)
            passages = [p for p in passages if p.score is None or p.score >= best_passage - PASSAGE_MARGIN]

        units = [unit for passage in passages for unit in split_units(passage)]
        if not units:
            raise ProviderError("no sentences to extract")

        # Score each unit with its heading, so "Minimum CGPA: 7.0." is judged
        # as a statement about the right company.
        scores = rerank_scores(
            request.question,
            [
                f"{u.passage.title} - {u.passage.section}: {u.text}" if u.passage.section else f"{u.passage.title}: {u.text}"
                for u in units
            ],
        )
        for unit, score in zip(units, scores):
            unit.score = score
        ranked = sorted(units, key=lambda u: -u.score)
        best = ranked[0]

        chosen: list[Unit] = []
        seen: set[str] = set()
        words = 0

        def take(unit: Unit) -> bool:
            nonlocal words
            key = re.sub(r"\W+", " ", unit.text.lower()).strip()
            n = len(unit.text.split())
            if key in seen or len(chosen) >= MAX_UNITS or (chosen and words + n > MAX_WORDS):
                return False
            seen.add(key)
            chosen.append(unit)
            words += n
            return True

        take(best)
        # A list is an answer set: if the best hit is a list item, its
        # siblings in the same passage usually belong to the same answer.
        if best.is_item:
            for unit in units:
                if unit.passage is best.passage and unit.is_item:
                    take(unit)
        for unit in ranked[1:]:
            if unit.score < best.score - UNIT_MARGIN:
                break
            take(unit)

        # Read in document order: by source number, then position in it.
        chosen.sort(key=lambda u: (u.passage.n, u.position))
        parts = []
        for unit in chosen:
            text = unit.text if unit.text[-1] in ".!?" else unit.text + "."
            parts.append(f"{text} [{unit.passage.n}]")
        return " ".join(parts)
