from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ModelProvider(StrEnum):
    GROQ = "groq"
    OLLAMA = "ollama"
    VLLM = "vllm"
    OPENAI = "openai"


class ModelHealth(BaseModel):
    is_healthy: bool = True
    latency_p95_ms: float = 0.0
    error_rate: float = 0.0
    in_flight: int = 0
    last_checked_at: float | None = None


class ModelSpec(BaseModel):
    name: str
    provider: ModelProvider
    model_id: str
    endpoint: str | None = None
    context_length: int = 32768
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    capabilities: list[str] = Field(default_factory=list)
    health: ModelHealth = Field(default_factory=ModelHealth)
    extra: dict[str, Any] = Field(default_factory=dict)
