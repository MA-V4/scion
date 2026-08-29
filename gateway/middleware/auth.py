from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates the Bearer token on every request. Bypassed in development."""

    EXEMPT_PATHS = {"/health", "/metrics", "/v1/models"}

    def __init__(self, app, valid_keys: set[str], dev_mode: bool = False) -> None:
        super().__init__(app)
        self._valid_keys = valid_keys
        self._dev_mode = dev_mode

    async def dispatch(self, request: Request, call_next):
        if self._dev_mode or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"}, status_code=401
            )

        key = auth.removeprefix("Bearer ").strip()
        if key not in self._valid_keys:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        return await call_next(request)
