"""Embedding and reranking models, loaded once and shared.

Both run on CPU and are read from the local Hugging Face cache. When both are
already cached, offline mode is switched on before the libraries are imported,
so starting the app never needs the network. On a machine that has never
downloaded them, the first start fetches them (about 180 MB) instead of failing.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger("placemate.models")

_lock = threading.Lock()
_embedder = None
_reranker = None


def model_cache_dir(model_id: str) -> Path:
    """Where huggingface_hub keeps a model (honours HF_HOME and HF_HUB_CACHE)."""
    hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    if os.environ.get("HF_HUB_CACHE"):
        hub = Path(os.environ["HF_HUB_CACHE"])
    return hub / f"models--{model_id.replace('/', '--')}"


def is_cached(model_id: str) -> bool:
    snapshots = model_cache_dir(model_id) / "snapshots"
    return snapshots.is_dir() and any(snapshots.iterdir())


def _prepare_environment() -> None:
    settings = get_settings()
    # Offline only when there is nothing to download; a fresh machine needs the Hub once.
    if settings.hf_offline and is_cached(settings.embedding_model) and is_cached(settings.reranker_model):
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
