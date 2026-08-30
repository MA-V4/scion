from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

import httpx

from gateway.models.registry import ModelSpec
from gateway.models.request import LLMRequest, LLMResponse, Message, Role, StreamChunk, Usage
from serving.backends.base import Backend


class OllamaBackend(Backend):
    def __init__(self, spec: ModelSpec) -> None:
        self._spec = spec
        self._base_url = spec.endpoint or "http://localhost:11434"
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120.0)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self._spec.model_id,
            "messages": request.messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        start = time.time()
        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.time() - start) * 1000

        return LLMResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": Message(
                        role=Role.ASSISTANT,
                        content=data["message"]["content"],
                    ),
                    "finish_reason": "stop",
                }
            ],
            usage=Usage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            ),
            routing_metadata={"latency_ms": latency_ms, "backend": "ollama"},
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        payload = {
            "model": self._spec.model_id,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                import json

                data = json.loads(line)
                yield StreamChunk(
                    id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    model=request.model,
                    choices=[
                        {
                            "index": 0,
                            "delta": {"content": data.get("message", {}).get("content", "")},
                            "finish_reason": "stop" if data.get("done") else None,
                        }
                    ],
                )

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
