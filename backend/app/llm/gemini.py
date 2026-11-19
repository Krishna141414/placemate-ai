"""Gemini provider (google-genai SDK)."""

from __future__ import annotations

import logging
import threading

from app.config import get_settings
from app.llm.base import LLMRequest, ProviderError

logger = logging.getLogger("placemate.llm.gemini")


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        self._client = None
        self._lock = threading.Lock()

    @property
    def model(self) -> str:
        return get_settings().gemini_model

    def available(self) -> tuple[bool, str]:
        if not get_settings().gemini_api_key:
            return False, "no API key"
        return True, ""

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from google import genai
                    from google.genai import types

                    settings = get_settings()
                    self._client = genai.Client(
                        api_key=settings.gemini_api_key,
                        http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1000),
                    )
        return self._client

    def generate(self, request: LLMRequest) -> str:
        from google.genai import errors, types

        try:
            response = self._get_client().models.generate_content(
                model=self.model,
                contents=request.prompt,
                config=types.GenerateContentConfig(
                    system_instruction=request.system,
                    temperature=0.1,
                    max_output_tokens=request.max_tokens,
                ),
            )
        except errors.APIError as exc:
            # Status code only. The message can echo request content.
            logger.warning("gemini_api_error", extra={"status": getattr(exc, "code", None)})
            raise ProviderError(f"API error {getattr(exc, 'code', '')}".strip()) from exc
        except Exception as exc:  # network errors, timeouts
            logger.warning("gemini_call_failed", extra={"error_type": type(exc).__name__})
            raise ProviderError(type(exc).__name__) from exc

        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ProviderError("empty response")
        return text
