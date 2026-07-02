"""Rate limiting in-memory para POST /auth/login y POST /auth/register."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

_AUTH_PATHS = frozenset({"/auth/login", "/auth/register"})
_store: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _is_allowed(key: str, *, max_requests: int, window_seconds: int) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _store[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True


def reset_auth_rate_limit_store() -> None:
    """Util para tests."""
    with _lock:
        _store.clear()


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "POST" and request.url.path in _AUTH_PATHS:
            settings = get_settings()
            if not _is_allowed(
                _client_key(request),
                max_requests=settings.auth_rate_limit_max,
                window_seconds=settings.auth_rate_limit_window_seconds,
            ):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiados intentos. Espera un momento e inténtalo de nuevo."},
                    headers={"Retry-After": str(settings.auth_rate_limit_window_seconds)},
                )
        return await call_next(request)
