from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    model: str = "fast"
    max_iterations: int = 20
    max_tokens_per_step: int = 1024
    token_budget: int = 32768
    timeout_s: float = 120.0
    max_tool_calls: int = 50
    allowed_tools: list[str] = field(default_factory=list)
    system_prompt: str = (
        "You are a helpful, precise assistant. "
        "When you need to use a tool, respond with:\n"
        'TOOL_CALL: {"name": "tool_name", "input": {...}}\n'
        "When you have a final answer, respond normally without TOOL_CALL."
    )


@dataclass
class AgentStep:
    iteration: int
    response: str
    tool_call: dict[str, Any] | None = None
    is_terminal: bool = False
    tokens_used: int = 0
    latency_ms: float = 0.0


@dataclass
class AgentTrace:
    task: str
    started_at: float
    finished_at: float = 0.0
    steps: list[AgentStep] = field(default_factory=list)
    tool_calls_made: int = 0
    total_tokens: int = 0
    termination_reason: str = "finished"
    final_answer: str | None = None
