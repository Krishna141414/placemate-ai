"""Reading documents from disk: front matter, cleaning, PDF text."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (metadata, body).

    Files without a YAML block return an empty dict and the whole text.
    A malformed block is treated as no front matter, never as an error,
    because uploaded files are untrusted.
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[match.end():]
