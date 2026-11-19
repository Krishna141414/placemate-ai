"""PII redaction for resume text and log lines.

Resume text passes through `redact_pii` before it reaches an embedding model
or an LLM. The same patterns back a logging filter, so contact details cannot
end up in a log file even if a message accidentally includes them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Indian mobile numbers: optional +91 / 91 / 091 / 0 prefix, then ten digits
# starting 6-9, with optional single spaces or hyphens between digits.
PHONE_RE = re.compile(r"(?<![\w.])(?:\+?0?91[\s-]*|0[\s-]?)?[6-9]\d(?:[\s-]?\d){8}(?!\d)")

PROFILE_LINK_RE = re.compile(
    r"\b(?:https?://)?(?:www\.)?(?:linkedin|github|twitter|x|instagram|facebook)\.[a-z.]+/[^\s,;]+",
    re.IGNORECASE,
)

_ADDRESS_LABEL_RE = re.compile(
    r"^(\s*(?:permanent\s+|current\s+|present\s+|residential\s+|home\s+)?(?:address|residence)\s*[:\-]\s*)(.+)$",
    re.IGNORECASE,
)
_PINCODE_RE = re.compile(r"\b[1-9]\d{2}\s?\d{3}\b")
_ADDRESS_WORDS_RE = re.compile(
    r"\b(flat|plot|door|house|h\.?\s?no|no\.|street|st\.|road|rd\.|cross|main|nagar|colony|layout|"
    r"apartment|apartments|residency|floor|block|near|opp\.?|lane|village|taluk|district|post)\b",
    re.IGNORECASE,
)

EMAIL_TOKEN = "[EMAIL REDACTED]"
PHONE_TOKEN = "[PHONE REDACTED]"
ADDRESS_TOKEN = "[ADDRESS REDACTED]"
LINK_TOKEN = "[LINK REDACTED]"


@dataclass
class RedactionResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _redact_addresses(text: str) -> tuple[str, int]:
    """Redact address lines.

    A line is treated as an address when it is labelled as one, or when it
    contains a six-digit PIN code together with at least one address word.
    """
    count = 0
    out_lines: list[str] = []
    for line in text.splitlines():
        labelled = _ADDRESS_LABEL_RE.match(line)
        if labelled:
            out_lines.append(f"{labelled.group(1)}{ADDRESS_TOKEN}")
            count += 1
            continue
        if _PINCODE_RE.search(line) and _ADDRESS_WORDS_RE.search(line):
            out_lines.append(ADDRESS_TOKEN)
            count += 1
            continue
        out_lines.append(line)
    return "\n".join(out_lines), count


def redact_pii(text: str) -> RedactionResult:
    """Remove emails, phone numbers, postal addresses and profile links."""
    if not text:
        return RedactionResult(text="", counts={"email": 0, "phone": 0, "address": 0, "link": 0})

    text, address_count = _redact_addresses(text)
    text, link_count = PROFILE_LINK_RE.subn(LINK_TOKEN, text)
    text, email_count = EMAIL_RE.subn(EMAIL_TOKEN, text)
    text, phone_count = PHONE_RE.subn(PHONE_TOKEN, text)
    return RedactionResult(
        text=text,
        counts={"email": email_count, "phone": phone_count, "address": address_count, "link": link_count},
    )


def scrub_for_log(text: str) -> str:
    """Cheap scrub used by the logging filter (emails and phone numbers)."""
    text = EMAIL_RE.sub(EMAIL_TOKEN, text)
    return PHONE_RE.sub(PHONE_TOKEN, text)
