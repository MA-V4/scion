from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class LLMRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str
    messages: list[Message]
    max_tokens: int = 1024
    temperature: float = 0.7
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"] | None = None


class LLMResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:8]}")
    object: str = "chat.completion"
    model: str
    choices: list[Choice]
    usage: Usage
    trace_id: str | None = None
    routing_metadata: dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    model: str
    choices: list[dict[str, Any]]
