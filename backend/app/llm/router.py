"""Provider routing with automatic fallback.

Order is always gemini -> local -> extractive, starting from the provider
named in `LLM_PROVIDER`. A provider is skipped when it is unavailable, when
it raises, or when its answer fails the caller's check (for example, an
answer with no valid citation). The result records which provider answered
and why earlier ones were passed over.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.config import get_settings
from app.llm.base import LLMRequest, LLMResult, Provider, ProviderError
from app.llm.extractive import ExtractiveProvider
from app.llm.gemini import GeminiProvider
from app.llm.local import LocalProvider

logger = logging.getLogger("placemate.llm")

ORDER = ("gemini", "local", "extractive")

_providers: dict[str, Provider] = {
    "gemini": GeminiProvider(),
    "local": LocalProvider(),
    "extractive": ExtractiveProvider(),
}


def get_provider(name: str) -> Provider:
    return _providers[name]


def provider_chain(start: str | None = None) -> list[Provider]:
    start = (start or get_settings().llm_provider or "gemini").lower()
    if start not in ORDER:
        start = "gemini"
    return [_providers[name] for name in ORDER[ORDER.index(start):]]


def provider_status() -> list[dict]:
    """What the UI shows about each provider."""
    configured = get_settings().llm_provider
    status = []
    for name in ORDER:
        provider = _providers[name]
        usable, reason = provider.available()
        status.append(
            {"name": name, "model": provider.model, "available": usable, "reason": reason, "configured": name == configured}
        )
    return status


def generate(
    request: LLMRequest,
    *,
    accept: Callable[[str], str | None] | None = None,
    start: str | None = None,
) -> LLMResult:
    """Run the chain until a provider gives an acceptable answer.

    `accept` returns None when the text is fine, or a short reason to reject
    it. The extractive provider is never rejected: it is the floor.
    """
    fallbacks: list[str] = []
    for provider in provider_chain(start):
        usable, reason = provider.available()
        if not usable:
            fallbacks.append(f"{provider.name}: {reason}")
            continue
        try:
            text = provider.generate(request)
        except ProviderError as exc:
            fallbacks.append(f"{provider.name}: {exc}")
            logger.info("provider_fallback", extra={"provider": provider.name, "reason": str(exc)})
            continue

        if accept is not None and provider.name != "extractive":
            rejection = accept(text)
            if rejection:
                fallbacks.append(f"{provider.name}: {rejection}")
                logger.info("provider_rejected", extra={"provider": provider.name, "reason": rejection})
                continue
        return LLMResult(text=text, provider=provider.name, model=provider.model, fallbacks=fallbacks)

    raise ProviderError("; ".join(fallbacks) or "no provider available")
