"""Prompt-injection defences.

Three places, three functions:

- `scan_user_input`       the question, before anything is retrieved
- `sanitize_document_text` document text at ingest (seeded and uploaded)
- `filter_output`          the model's answer, before the user sees it

The scanner is a set of patterns over normalised text. It is deliberately
conservative: it looks for attempts to override instructions, extract the
system prompt, switch roles or pull out secrets, and leaves ordinary placement
questions alone. It is one layer; the prompt also fences retrieved text as
data, and refusal and citation checks limit what a successful injection could
achieve.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# A marker placed in the system prompt. If it ever appears in an answer, the
# model is leaking its instructions and the answer is discarded.
CANARY = "PM-CANARY-7F3A91"

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

_OVERRIDE_TARGET = r"(?:instruction|instructions|rule|rules|prompt|prompts|guideline|guidelines|direction|directions|context|message|messages|constraint|constraints|policy|policies)"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard|forget|override|bypass|skip|drop|discard)\b[^.\n]{0,40}?"
            r"\b(?:all|any|every|the|your|previous|prior|above|earlier|preceding|former|system|safety)\b[^.\n]{0,30}?"
            rf"\b{_OVERRIDE_TARGET}\b"
        ),
    ),
    (
        "instruction_override",
        re.compile(r"\b(?:do not|don't|dont|stop)\s+(?:follow|obey|use|apply)\w*\b[^.\n]{0,30}?" rf"\b{_OVERRIDE_TARGET}\b"),
    ),
    (
        "instruction_override",
        re.compile(r"\bnew\s+(?:instruction|instructions|rules|system prompt)\s*[:\-]"),
    ),
    (
        "prompt_extraction",
        re.compile(
            r"\b(?:reveal|show|print|repeat|display|output|leak|expose|share|tell me|give me|what is|what are|write out|dump)\b"
            r"[^.\n]{0,40}?\b(?:system|hidden|initial|original|secret|internal|developer)\b[^.\n]{0,15}?"
            r"\b(?:prompt|prompts|instruction|instructions|message|rules|configuration|config)\b"
        ),
    ),
    (
        "prompt_extraction",
        re.compile(r"\b(?:repeat|print|output)\b[^.\n]{0,25}?\b(?:everything|all|the text|the words)\b[^.\n]{0,20}?\babove\b"),
    ),
    (
        "role_hijack",
        re.compile(
            r"\b(?:you are now|you're now|from now on you are|act as|pretend to be|pretend you are|roleplay as|"
            r"behave as|simulate)\b[^.\n]{0,30}?\b(?:dan|developer|admin|administrator|root|system|unrestricted|"
            r"unfiltered|uncensored|jailbroken|evil|a different|another|no longer)\b"
        ),
    ),
    (
        "role_hijack",
        re.compile(r"\b(?:developer|debug|admin|god|sudo|dan|jailbreak)\s+mode\b|\bjailbreak\b|\bdo anything now\b"),
    ),
    (
        "role_spoofing",
        re.compile(
            r"(?:^|\n)\s*(?:system|assistant|developer)\s*[:>]|<\|?(?:im_start|im_end|system|endoftext)\|?>|\[/?inst\]|"
            # A markdown heading that is only "System" / "Instructions" (optionally
            # "prompt" or "message"), not ordinary headings such as
            # "## System Design Basics Round".
            r"(?:^|\n)\s*#{1,6}\s*(?:system|instructions?)(?:\s+(?:prompt|message))?\s*(?::|\n|$)"
        ),
    ),
    (
        "secret_exfiltration",
        re.compile(
            r"\b(?:api[\s_-]?key|secret[\s_-]?key|access token|password hash|password hashes|env(?:ironment)? variables?|"
            r"database dump|dump (?:the )?database|credentials)\b|(?<!\w)\.env\b"
        ),
    ),
    (
        "secret_exfiltration",
        re.compile(
            r"\b(?:list|show|give|send|export|dump|print)\b[^.\n]{0,30}?\b(?:all|every|other)\b[^.\n]{0,20}?"
            r"\b(?:students?|users?)\b[^.\n]{0,25}?\b(?:passwords?|emails?|phone numbers?|resumes?|cgpas?|records?)\b"
        ),
    ),
    (
        "answer_forcing",
        re.compile(r"\b(?:respond|reply|answer)\s+(?:only\s+)?with\b[^.\n]{0,40}?\b(?:regardless|no matter|always|instead)\b"),
    ),
    (
        "answer_forcing",
        re.compile(r"\b(?:tell|inform|say to)\s+(?:every|all|each)\s+(?:student|students|user|users|one)\b[^.\n]{0,60}?\b(?:that|to)\b"),
    ),
]

BLOCK_LABELS = {
    "instruction_override": "tries to override the assistant's instructions",
    "prompt_extraction": "asks for the hidden system prompt",
    "role_hijack": "tries to switch the assistant into another role",
    "role_spoofing": "imitates a system or assistant message",
    "secret_exfiltration": "asks for secrets or other people's data",
    "answer_forcing": "tries to force a fixed answer",
}


@dataclass
class GuardResult:
    blocked: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        return [BLOCK_LABELS.get(reason, reason) for reason in self.reasons]


def normalise(text: str) -> str:
    """Fold tricks that hide trigger words: unicode forms, zero-width
    characters, spaced-out letters and digit-for-letter swaps."""
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH).lower()
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    # "i g n o r e" -> "ignore"
    text = re.sub(r"\b(?:[a-z0-9] ){3,}[a-z0-9]\b", lambda m: m.group(0).replace(" ", ""), text)
    return text


def _matches(text: str) -> list[str]:
    plain = normalise(text)
    variants = (plain, plain.translate(_LEET))
    reasons: list[str] = []
    for name, pattern in _PATTERNS:
        if name in reasons:
            continue
        if any(pattern.search(variant) for variant in variants):
            reasons.append(name)
    return reasons


def scan_user_input(text: str) -> GuardResult:
    reasons = _matches(text)
    return GuardResult(blocked=bool(reasons), reasons=reasons)


def sanitize_document_text(text: str) -> tuple[str, list[str]]:
    """Drop instruction-like lines from a document before it is indexed.

    Returns the cleaned text and the removed lines. A document is reference
    material; a line that addresses the model ("ignore previous
    instructions", "SYSTEM: ...") has no business being retrieved.
    """
    kept: list[str] = []
    removed: list[str] = []
    for line in text.splitlines():
        if line.strip() and _matches(line):
            removed.append(line.strip()[:200])
        else:
            kept.append(line)
    return "\n".join(kept), removed


_CITATION_RE = re.compile(r"\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\]")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:https?:)?//[^)]*\)")
_HTML_TAG_RE = re.compile(r"</?(?:script|iframe|img|object|embed|style|link|meta|form|input|svg)[^>]*>", re.IGNORECASE)
_BARE_URL_RE = re.compile(r"https?://\S+")


def normalise_citations(text: str, n_sources: int) -> tuple[str, list[int]]:
    """Rewrite `[1, 2]` as `[1][2]` and drop numbers that are not sources."""
    used: list[int] = []

    def _replace(match: re.Match[str]) -> str:
        valid = []
        for part in match.group(1).split(","):
            number = int(part.strip())
            if 1 <= number <= n_sources:
                valid.append(number)
                if number not in used:
                    used.append(number)
        return "".join(f"[{number}]" for number in valid)

    cleaned = _CITATION_RE.sub(_replace, text)
    cleaned = re.sub(r"[ \t]+([.,;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip(), used


def filter_output(text: str, n_sources: int, allowed_text: str = "") -> tuple[str, list[int], list[str]]:
    """Clean a model answer before display.

    Returns (text, citations, notes). An empty text means the answer must be
    discarded (it leaked the system prompt).
    """
    notes: list[str] = []
    if CANARY in text:
        return "", [], ["system prompt leak"]

    if _MD_IMAGE_RE.search(text) or _HTML_TAG_RE.search(text):
        text = _HTML_TAG_RE.sub("", _MD_IMAGE_RE.sub("", text))
        notes.append("removed embedded markup")

    # Links are a way to smuggle data out. Keep the label, drop the target,
    # and drop bare URLs that do not appear in the retrieved sources.
    if _MD_LINK_RE.search(text):
        text = _MD_LINK_RE.sub(r"\1", text)
        notes.append("removed external link")

    def _url(match: re.Match[str]) -> str:
        url = match.group(0).rstrip(".,);")
        if allowed_text and url in allowed_text:
            return match.group(0)
        notes.append("removed external link")
        return ""

    text = _BARE_URL_RE.sub(_url, text)

    before = len(_CITATION_RE.findall(text))
    text, citations = normalise_citations(text, n_sources)
    if before and len(_CITATION_RE.findall(text)) < before:
        notes.append("removed invalid citation")
    return text, citations, list(dict.fromkeys(notes))
