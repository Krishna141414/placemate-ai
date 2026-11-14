"""HTTP-level protections that apply to every request.

- `RequestContextMiddleware`: request id, access log line, and a last-resort
  catch so an unexpected exception never reaches the client as a stack trace.
- `SecurityHeadersMiddleware`: standard hardening headers.
- `OriginCheckMiddleware`: rejects state-changing requests from another site.
  CORS alone does not stop a cross-site form post, and the session is a
  cookie, so this closes CSRF.

All three are plain ASGI middleware so that streaming (SSE) responses pass
through untouched.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings
from app.errors import error_response
from app.logging_conf import reset_request_id, set_request_id

logger = logging.getLogger("placemate.http")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:16]
        token = set_request_id(request_id)
        started = time.perf_counter()
        status_holder = {"status": 500, "started": False}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                status_holder["started"] = True
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # Full details go to the log, keyed by request id. The client gets
            # a generic message and the id to quote.
            logger.exception("unhandled_exception", extra={"path": scope.get("path")})
            if not status_holder["started"]:
                response = error_response(
                    500, "internal_error", "Something went wrong on our side. Please try again."
                )
                await response(scope, receive, send_wrapper)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_holder["status"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            reset_request_id(token)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        settings = get_settings()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                headers["Cross-Origin-Resource-Policy"] = "same-site"
                if path.startswith(DOCS_PATHS):
                    # Swagger UI needs its CDN assets and an inline bootstrap script.
                    headers["Content-Security-Policy"] = (
                        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                        "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
                    )
                else:
                    # The API serves JSON only, so nothing may be loaded or framed.
                    headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
                    headers["Cache-Control"] = "no-store"
                if settings.cookie_secure:
                    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_wrapper)


class OriginCheckMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method", "GET") in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        origin = Headers(scope=scope).get("origin")
        allowed = get_settings().frontend_origin.rstrip("/")
        # Browsers always send Origin on cross-site unsafe requests. Requests
        # without it come from non-browser clients, which hold no ambient cookie.
        if origin is not None and origin.rstrip("/") != allowed:
            logger.warning("origin_rejected", extra={"origin": origin, "path": scope.get("path")})
            response = error_response(403, "origin_not_allowed", "This request came from an unexpected site.")
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
