from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# TODO: replace in-memory store with Redis token bucket for multi-instance deployments
_buckets: dict[str, tuple[float, float]] = {}

REQUESTS_PER_MINUTE = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple token bucket rate limiter per API key. Uses Redis in production."""

    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("Authorization", "anonymous")
        now = time.time()

        tokens, last_refill = _buckets.get(key, (REQUESTS_PER_MINUTE, now))
        elapsed = now - last_refill
        tokens = min(REQUESTS_PER_MINUTE, tokens + elapsed * (REQUESTS_PER_MINUTE / 60))

        if tokens < 1:
            return JSONResponse(
                {"error": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "1"},
            )

        _buckets[key] = (tokens - 1, now)
        return await call_next(request)
