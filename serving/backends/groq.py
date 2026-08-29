from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator

import httpx

from gateway.models.request import LLMRequest, LLMResponse, Message, Role, StreamChunk, Usage
from gateway.models.registry import ModelSpec
from serving.backends.base import Backend


class GroqBackend(Backend):

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, spec: ModelSpec, api_key: str) -> None:
        self._spec = spec
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self._spec.model_id,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        start = time.time()
        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.time() - start) * 1000

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": Message(
                        role=Role.ASSISTANT,
                        content=choice["message"]["content"],
                    ),
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
            ],
            usage=Usage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
            routing_metadata={
                "latency_ms": latency_ms,
                "backend": "groq",
                "queue_time_ms": usage.get("queue_time", 0) * 1000,
            },
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        payload = {
            "model": self._spec.model_id,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line.removeprefix("data: ").strip()
                if raw == "[DONE]":
                    return
                data = json.loads(raw)
                choice = data["choices"][0]
                delta = choice.get("delta", {})
                yield StreamChunk(
                    id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
                    model=request.model,
                    choices=[{
                        "index": 0,
                        "delta": {"content": delta.get("content", "")},
                        "finish_reason": choice.get("finish_reason"),
                    }],
                )

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()