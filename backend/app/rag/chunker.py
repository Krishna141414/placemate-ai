"""Heading-aware chunking.

A document is split at markdown headings, and each section is packed into
chunks of about 180 words with a short overlap. Every chunk keeps its heading
path ("Nimbusware Technologies > Eligibility"), because a line such as
"Minimum CGPA: 7.0" means nothing without knowing whose rule it is.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.rag.loader import SourceDoc

CHUNKER_VERSION = "2"
MAX_WORDS = 180
OVERLAP_WORDS = 30
MIN_WORDS = 8

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_TITLE_NOISE_RE = re.compile(r"\s*\((?:fictional|test fixture)[^)]*\)\s*", re.IGNORECASE)


@dataclass
class Chunk:
    id: str
    doc_key: str
    title: str
    doc_type: str
    company_id: str | None
    section: str
    text: str  # what the user sees in a source card
    index_text: str  # what is embedded and searched: heading path + text

    def to_dict(self) -> dict:
        return asdict(self)


def _split_sections(body: str) -> list[tuple[list[str], str]]:
    """[(heading path, section text)] in document order."""
    sections: list[tuple[list[str], str]] = []
    path: list[tuple[int, str]] = []
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            sections.append(([title for _, title in path], text))
        buffer.clear()

    for line in body.split("\n"):
        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, heading.group(2).strip()))
        else:
            buffer.append(line)
    flush()
    return sections


def _blocks(section_text: str) -> list[str]:
    """Paragraphs and individual list items, in order."""
    blocks: list[str] = []
    for paragraph in re.split(r"\n\s*\n", section_text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        lines = paragraph.split("\n")
        is_list = sum(bool(re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line)) for line in lines) >= max(1, len(lines) // 2)
        if is_list:
            item: list[str] = []
            for line in lines:
                if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line) and item:
                    blocks.append(" ".join(item))
                    item = []
                item.append(line.strip())
            if item:
                blocks.append(" ".join(item))
        else:
            blocks.append(" ".join(line.strip() for line in lines))
    return blocks


def _split_long(block: str) -> list[str]:
    """Break a block that is longer than a chunk at sentence boundaries."""
    words = block.split()
    if len(words) <= MAX_WORDS:
        return [block]
    pieces: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in _SENTENCE_SPLIT_RE.split(block):
        n = len(sentence.split())
        if n > MAX_WORDS:  # a single enormous sentence: hard split
            if current:
                pieces.append(" ".join(current))
                current, count = [], 0
            sentence_words = sentence.split()
            for i in range(0, n, MAX_WORDS):
                pieces.append(" ".join(sentence_words[i : i + MAX_WORDS]))
            continue
        if count + n > MAX_WORDS and current:
            pieces.append(" ".join(current))
            current, count = [], 0
        current.append(sentence)
        count += n
    if current:
        pieces.append(" ".join(current))
    return pieces


def _pack(blocks: list[str]) -> list[str]:
    """Greedy packing with a word overlap carried from the previous chunk."""
    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for block in (piece for b in blocks for piece in _split_long(b)):
        n = len(block.split())
        if current and count + n > MAX_WORDS:
            chunks.append("\n".join(current))
            tail = " ".join("\n".join(current).split()[-OVERLAP_WORDS:])
            # Carry the overlap only when the next block still fits beside it.
            if n + OVERLAP_WORDS <= MAX_WORDS:
                current, count = [f"... {tail}"], OVERLAP_WORDS
            else:
                current, count = [], 0
        current.append(block)
        count += n
    if current:
        chunks.append("\n".join(current))
    return chunks


def clean_title(title: str) -> str:
    return _TITLE_NOISE_RE.sub(" ", title).strip()


def chunk_document(doc: SourceDoc) -> list[Chunk]:
    title = clean_title(doc.title)
    chunks: list[Chunk] = []
    for path, text in _split_sections(doc.text):
        # The first heading usually repeats the document title.
        trail = [clean_title(p) for p in path]
        if trail and trail[0].lower() == title.lower():
            trail = trail[1:]
        section = " > ".join(trail)
        heading = " > ".join([title, *trail])
        for body in _pack(_blocks(text)):
            if len(body.split()) < MIN_WORDS and not trail:
                continue  # stray line such as "(Fictional sample company.)"
            chunks.append(
                Chunk(
                    id=f"{doc.doc_key}#{len(chunks)}",
                    doc_key=doc.doc_key,
                    title=title,
                    doc_type=doc.doc_type,
                    company_id=doc.company_id,
                    section=section,
                    text=body,
                    index_text=f"{heading}\n{body}",
                )
            )
    return chunks
