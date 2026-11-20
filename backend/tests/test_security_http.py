"""HTTP-level protections: headers, CORS, origin check, rate limit, error shape."""

from __future__ import annotations

import json
import logging

from app.logging_conf import JsonFormatter, PiiScrubFilter
from app.security.rate_limit import RateLimiter, classify
from app.seed import DEMO_STUDENT_EMAIL

ALLOWED_ORIGIN = "http://localhost:3000"


def test_security_headers_on_every_response(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]


def test_security_headers_on_error_responses(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_docs_and_openapi_are_served(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "PlaceMate API"
    assert "/api/auth/login" in schema["paths"]


def test_cors_allows_only_the_frontend_origin(client):
    allowed = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
    assert allowed.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert allowed.headers["access-control-allow-credentials"] == "true"

    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_cors_preflight_from_another_origin_is_refused(client):
    response = client.options(
        "/api/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_unsafe_request_from_another_origin_is_blocked(client):
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_STUDENT_EMAIL, "password": "Student@123"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"
    assert "set-cookie" not in response.headers


def test_unsafe_request_from_the_frontend_origin_is_allowed(client):
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_STUDENT_EMAIL, "password": "Student@123"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert response.status_code == 200


def test_login_is_rate_limited(client):
    payload = {"email": DEMO_STUDENT_EMAIL, "password": "wrong-password"}
    statuses = [client.post("/api/auth/login", json=payload).status_code for _ in range(10)]
    assert statuses == [401] * 10

    blocked = client.post("/api/auth/login", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_probe_endpoint_has_its_own_tight_limit(student_client):
    statuses = [student_client.get("/api/meta/ping").status_code for _ in range(6)]
    assert statuses == [200] * 5 + [429]
    # A different route class is unaffected.
    assert student_client.get("/api/auth/me").status_code == 200


def test_health_is_not_rate_limited(client):
    assert all(client.get("/health").status_code == 200 for _ in range(80))


def test_rate_limiter_window_slides():
    limiter = RateLimiter(window_seconds=60)
    for second in range(3):
        assert limiter.check("1.2.3.4", "auth", limit=3, now=float(second)) == (True, 0)
    allowed, retry_after = limiter.check("1.2.3.4", "auth", limit=3, now=10.0)
    assert not allowed and retry_after == 50
    # Another client and another class have their own budgets.
    assert limiter.check("5.6.7.8", "auth", limit=3, now=10.0)[0]
    assert limiter.check("1.2.3.4", "default", limit=3, now=10.0)[0]
    # After the window has passed the client is allowed again.
    assert limiter.check("1.2.3.4", "auth", limit=3, now=61.0)[0]


def test_route_classes():
    assert classify("/health") is None
    assert classify("/docs") is None
    assert classify("/api/auth/login") == "auth"
    assert classify("/api/meta/ping") == "probe"
    assert classify("/api/ask") == "default"


def test_unhandled_exception_returns_a_clean_500(client):
    response = client.get("/api/_test/boom")
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert "Traceback" not in response.text
    assert "secret internal detail" not in response.text
    assert "RuntimeError" not in response.text
    # Hardening headers are still present on the failure path.
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_not_found_uses_the_error_envelope(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["request_id"]


def test_method_not_allowed_uses_the_error_envelope(client):
    response = client.delete("/api/auth/login")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_malformed_json_is_a_422_not_a_500(client):
    response = client.post(
        "/api/auth/login", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def _format(record_kwargs: dict, message: str) -> dict:
    record = logging.LogRecord("placemate.test", logging.INFO, __file__, 1, message, (), None)
    for key, value in record_kwargs.items():
        setattr(record, key, value)
    PiiScrubFilter().filter(record)
    return json.loads(JsonFormatter().format(record))


def test_log_lines_are_json_with_request_id():
    entry = _format({"path": "/api/ask", "status": 200}, "request")
    assert entry["message"] == "request"
    assert entry["level"] == "INFO"
    assert entry["path"] == "/api/ask"
    assert entry["status"] == 200
    assert "request_id" in entry and "ts" in entry


def test_logs_never_contain_emails_or_phone_numbers():
    entry = _format(
        {"note": "call +91 90000 12345"},
        "resume for ananya.rao@krit.example phone 9000054321",
    )
    text = json.dumps(entry)
    assert "ananya.rao@krit.example" not in text
    assert "9000054321" not in text
    assert "90000 12345" not in text
    assert "[EMAIL REDACTED]" in text and "[PHONE REDACTED]" in text


def test_security_headers_are_readable_by_the_frontend(client):
    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
    exposed = response.headers["access-control-expose-headers"]
    for name in ("X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "Retry-After"):
        assert name in exposed
