from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from gateway.models.request import LLMRequest, LLMResponse, StreamChunk
from serving.backends.base import Backend


class VLLMBackend(Backend):
    """Adapter for vLLM's OpenAI-compatible server."""

    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        # TODO: POST to /v1/chat/completions, parse response into LLMResponse
        raise NotImplementedError

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        # TODO: streaming POST to /v1/chat/completions
        raise NotImplementedError
        yield

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
