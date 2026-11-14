"""In-memory sliding-window rate limiter.

One process, so no shared store is needed. Each (client, route class) pair
keeps the timestamps of its recent requests; a request is refused once the
window is full. Limits come from settings.
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque

from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.errors import error_response

WINDOW_SECONDS = 60.0
EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")


class RateLimiter:
    def __init__(self, window_seconds: float = WINDOW_SECONDS) -> None:
        self.window = window_seconds
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, client: str, route_class: str, limit: int, now: float | None = None) -> tuple[bool, int]:
        """Record one request. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[(client, route_class)]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = max(1, math.ceil(self.window - (now - hits[0])))
                return False, retry_after
            hits.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def classify(path: str) -> str | None:
    """Map a path to its limit class, or None when the path is exempt."""
    if path.startswith(EXEMPT_PREFIXES):
        return None
    if path.startswith("/api/auth/login"):
        return "auth"
    if path.startswith("/api/meta/ping"):
        return "probe"
    return "default"


def limit_for(route_class: str) -> int:
    settings = get_settings()
    return {
        "auth": settings.auth_rate_limit_per_minute,
        "probe": settings.probe_rate_limit_per_minute,
    }.get(route_class, settings.rate_limit_per_minute)


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        route_class = classify(scope.get("path", ""))
        if route_class is None:
            await self.app(scope, receive, send)
            return

        # The socket peer address. X-Forwarded-For is not trusted because a
        # client can set it to anything.
        client = scope.get("client")
        client_id = client[0] if client else "unknown"
        allowed, retry_after = limiter.check(client_id, route_class, limit_for(route_class))
        if allowed:
            await self.app(scope, receive, send)
            return

        response = error_response(
            429,
            "rate_limited",
            f"Too many requests. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
        await response(scope, receive, send)
