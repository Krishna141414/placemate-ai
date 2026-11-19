"""Embedding and reranking models, loaded once and shared.

Both run on CPU and are read from the local Hugging Face cache. Offline mode
is switched on before the libraries are imported, so starting the app never
needs the network.
"""

from __future__ import annotations

import logging
import os
import threading
import time

import numpy as np

from app.config import get_settings

logger = logging.getLogger("placemate.models")

_lock = threading.Lock()
_embedder = None
_reranker = None


def _prepare_environment() -> None:
    if get_settings().hf_offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_VERBOSITY", "error")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    # Offline mode makes these libraries warn that the Hub is unreachable on
    # every load. That is expected here, so only real errors are shown.
    for name in ("huggingface_hub", "sentence_transformers", "transformers"):
        logging.getLogger(name).setLevel(logging.ERROR)


def get_embedder():
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                _prepare_environment()
                from sentence_transformers import SentenceTransformer

                started = time.perf_counter()
                _embedder = SentenceTransformer(get_settings().embedding_model, device="cpu")
                logger.info("embedder_loaded", extra={"seconds": round(time.perf_counter() - started, 2)})
    return _embedder


def get_reranker():
    global _reranker
    if _reranker is None:
        with _lock:
            if _reranker is None:
                _prepare_environment()
                from sentence_transformers import CrossEncoder

                started = time.perf_counter()
                _reranker = CrossEncoder(get_settings().reranker_model, device="cpu")
                logger.info("reranker_loaded", extra={"seconds": round(time.perf_counter() - started, 2)})
    return _reranker


def embed(texts: list[str]) -> np.ndarray:
    """Unit-length float32 vectors, so inner product equals cosine similarity."""
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    vectors = get_embedder().encode(
        texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True
    )
    return np.asarray(vectors, dtype="float32")


def rerank_scores(query: str, passages: list[str]) -> list[float]:
    """Cross-encoder relevance logits for (query, passage) pairs."""
    if not passages:
        return []
    scores = get_reranker().predict([(query, passage) for passage in passages], batch_size=16, show_progress_bar=False)
    return [float(score) for score in scores]
