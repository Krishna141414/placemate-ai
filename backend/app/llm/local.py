"""Local provider: a small instruct model from the Hugging Face cache, on CPU.

Used when Gemini is not configured or fails. The model is loaded on first use
(about a gigabyte), so the app starts quickly when it is never needed.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from app.config import get_settings
from app.llm.base import LLMRequest, ProviderError

logger = logging.getLogger("placemate.llm.local")

# A 0.5B model on CPU: keep the prompt short enough to answer in seconds.
MAX_PASSAGES = 3
MAX_PASSAGE_CHARS = 700


def _cache_dir_for(model_id: str) -> Path:
    hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    if os.environ.get("HF_HUB_CACHE"):
        hub = Path(os.environ["HF_HUB_CACHE"])
    return hub / f"models--{model_id.replace('/', '--')}"


class LocalProvider:
    name = "local"

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()
        self._failed: str | None = None

    @property
    def model(self) -> str:
        return get_settings().local_model

    def available(self) -> tuple[bool, str]:
        if self._failed:
            return False, self._failed
        if self._model is None and not _cache_dir_for(self.model).exists():
            return False, "model not in local cache"
        return True, ""

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from app.rag.models import _prepare_environment

            _prepare_environment()
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer

                started = time.perf_counter()
                self._tokenizer = AutoTokenizer.from_pretrained(self.model)
                self._model = AutoModelForCausalLM.from_pretrained(self.model, torch_dtype=torch.float32)
                self._model.eval()
                logger.info("local_model_loaded", extra={"seconds": round(time.perf_counter() - started, 1)})
            except Exception as exc:
                self._failed = f"could not load ({type(exc).__name__})"
                logger.warning("local_model_load_failed", extra={"error_type": type(exc).__name__})
                raise ProviderError(self._failed) from exc

    def generate(self, request: LLMRequest) -> str:
        self._load()
        import torch

        from app.rag.prompts import build_prompt

        # Rebuild the prompt with fewer, shorter passages for speed.
        passages = [
            type(p)(n=p.n, title=p.title, section=p.section, text=p.text[:MAX_PASSAGE_CHARS], score=p.score)
            for p in request.passages[:MAX_PASSAGES]
        ]
        messages = [
            {"role": "system", "content": request.system},
            {"role": "user", "content": build_prompt(request.question, passages)},
        ]
        try:
            inputs = self._tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
            )
            with self._lock, torch.inference_mode():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=min(request.max_tokens, get_settings().local_max_new_tokens),
                    do_sample=False,
                    repetition_penalty=1.1,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            text = self._tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        except Exception as exc:
            logger.warning("local_generation_failed", extra={"error_type": type(exc).__name__})
            raise ProviderError(type(exc).__name__) from exc
        if not text:
            raise ProviderError("empty response")
        return text
