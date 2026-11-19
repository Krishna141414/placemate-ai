"""Application factory.

    uvicorn app.main:app --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.errors import register_error_handlers
from app.logging_conf import configure_logging
from app.security.headers import OriginCheckMiddleware, RequestContextMiddleware, SecurityHeadersMiddleware
from app.security.rate_limit import RateLimitMiddleware
from app.seed import seed_demo_data

logger = logging.getLogger("placemate.app")

DESCRIPTION = """
PlaceMate API: cited answers over placement documents (RAG), deterministic
tools for eligibility, resume matching and application tracking, and a prep
agent that asks for approval before saving anything.

Log in with `POST /api/auth/login`. The session is an httpOnly cookie.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.db_url)
    with SessionLocal() as db:
        seed_demo_data(db)
    # Load (or build) the search index and warm the reranker, so the first
    # question is not the one that pays for model loading.
    from app.rag.index import IndexStore
    from app.rag.models import rerank_scores

    with SessionLocal() as db:
        index = IndexStore.ensure(db)
    rerank_scores("warm up", ["warm up"])
    logger.info("index_ready", extra={"documents": index.document_count, "chunks": len(index)})
    logger.info("startup_complete", extra={"env": settings.app_env, "provider": settings.llm_provider})
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_dir)

    app = FastAPI(
        title="PlaceMate API",
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
    )

    register_error_handlers(app)

    # Middleware runs outermost-last-added. Resulting order for a request:
    # CORS -> security headers -> request context -> origin check -> rate limit -> routes
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(OriginCheckMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin.rstrip("/")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )

    from app.api import ask, auth, meta

    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(ask.router)

    return app


app = create_app()
