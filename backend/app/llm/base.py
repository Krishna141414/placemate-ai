"""Shared types for LLM providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class ProviderError(Exception):
    """A provider could not produce an answer. The router moves to the next one."""


@dataclass
class Passage:
    """One numbered source given to the model."""

    n: int
    title: str
    section: str
    text: str
    score: float | None = None  # retrieval score of the passage


@dataclass
class LLMRequest:
    system: str
    prompt: str
    question: str
    passages: list[Passage]
    max_tokens: int = 500


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    fallbacks: list[str] = field(default_factory=list)  # "gemini: no API key", ...


class Provider(Protocol):
    name: str

    @property
    def model(self) -> str: ...

    def available(self) -> tuple[bool, str]:
        """(usable, reason when not usable)."""
        ...

    def generate(self, request: LLMRequest) -> str: ...
