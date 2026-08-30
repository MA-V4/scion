from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from gateway.models.registry import ModelSpec
from gateway.models.request import LLMRequest, LLMResponse, Message, Role, StreamChunk, Usage
from serving.backends.base import Backend

log = structlog.get_logger()


class GroqBackend(Backend):
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, spec: ModelSpec, api_key: str) -> None:
        self._spec = spec
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def _serialise_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.name:
                msg["name"] = m.name
            result.append(msg)
        return result

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._spec.model_id,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice or "auto"

        log.info("groq.request", model=self._spec.model_id, message_count=len(payload["messages"]))

        start = time.time()
        resp = await self._client.post("/chat/completions", json=payload)

        if resp.status_code >= 400:
            log.error("groq.error", status=resp.status_code, body=resp.text)

        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.time() - start) * 1000

        choice = data["choices"][0]
        usage = data.get("usage", {})
        message = choice["message"]

        return LLMResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": Message(
                        role=Role.ASSISTANT,
                        content=message.get("content") or "",
                    ),
                    "finish_reason": choice.get("finish_reason", "stop"),
                    "tool_calls": message.get("tool_calls"),
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
        payload: dict[str, Any] = {
            "model": self._spec.model_id,
            "messages": self._serialise_messages(request.messages),
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
                    choices=[
                        {
                            "index": 0,
                            "delta": {"content": delta.get("content", "")},
                            "finish_reason": choice.get("finish_reason"),
                        }
                    ],
                )

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()