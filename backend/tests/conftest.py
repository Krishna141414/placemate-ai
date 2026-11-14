"""Shared test setup.

Environment variables are set before the app is imported, so tests never
touch the real database, never call a paid API and never depend on `.env`.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="placemate-tests-"))

os.environ.update(
    {
        "APP_ENV": "test",
        "SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256-signing",
        "STORAGE_DIR": str(_TMP_ROOT / "storage"),
        "DATABASE_URL": "",
        "LLM_PROVIDER": "extractive",
        "GEMINI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "FRONTEND_ORIGIN": "http://localhost:3000",
        "COOKIE_SECURE": "false",
        "RATE_LIMIT_PER_MINUTE": "60",
        "AUTH_RATE_LIMIT_PER_MINUTE": "10",
        "PROBE_RATE_LIMIT_PER_MINUTE": "5",
        "MAX_UPLOAD_MB": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }
)

import pytest  # noqa: E402
from fastapi import Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db import SessionLocal  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import (  # noqa: E402
    AgentRun,
    Application,
    Conversation,
    Document,
    Event,
    Message,
    PrepPlan,
)
from app.security.auth import require_coordinator  # noqa: E402
from app.security.rate_limit import limiter  # noqa: E402
from app.seed import (  # noqa: E402
    DEMO_COORDINATOR_EMAIL,
    DEMO_COORDINATOR_PASSWORD,
    DEMO_STUDENT_EMAIL,
    DEMO_STUDENT_PASSWORD,
)


@pytest.fixture(scope="session")
def app():
    application = create_app()

    # Test-only routes: one that always crashes, one that needs a coordinator.
    @application.get("/api/_test/boom")
    def _boom():
        raise RuntimeError("secret internal detail that must not leak")

    @application.get("/api/_test/coordinator-only")
    def _coordinator_only(_user=Depends(require_coordinator)):
        return {"ok": True}

    with TestClient(application):
        yield application
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state(app):
    """Each test starts with an empty rate limiter and no leftover activity."""
    limiter.reset()
    yield
    limiter.reset()
    with SessionLocal() as db:
        for model in (Message, Conversation, PrepPlan, AgentRun, Application, Event):
            db.query(model).delete()
        db.query(Document).filter(Document.source == "upload").delete()
        db.commit()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db(app):
    with SessionLocal() as session:
        yield session


def _login(app, email: str, password: str) -> TestClient:
    test_client = TestClient(app, raise_server_exceptions=False)
    response = test_client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    limiter.reset()
    return test_client


@pytest.fixture
def student_client(app) -> TestClient:
    return _login(app, DEMO_STUDENT_EMAIL, DEMO_STUDENT_PASSWORD)


@pytest.fixture
def coordinator_client(app) -> TestClient:
    return _login(app, DEMO_COORDINATOR_EMAIL, DEMO_COORDINATOR_PASSWORD)
