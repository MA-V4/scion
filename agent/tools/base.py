from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ToolPermission(StrEnum):
    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    EXECUTE = "execute"


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """
    Abstract interface for all agent tools.
    Every tool declares its name, description, input schema, and required permissions.
    The agent cannot call a tool it does not have permission for.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        raise NotImplementedError

    @property
    @abstractmethod
    def permissions(self) -> set[ToolPermission]:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, input: BaseModel) -> ToolResult:
        raise NotImplementedError

    def to_function_schema(self) -> dict[str, Any]:
        """Return the OpenAI-style function calling schema for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema.model_json_schema(),
        }


class ToolRegistry:
    """Central registry of available tools. Enforces permission checks."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name]

    def list_schemas(self, allowed: set[str] | None = None) -> list[dict[str, Any]]:
        tools = self._tools.values()
        if allowed is not None:
            tools = [t for t in tools if t.name in allowed]
        return [t.to_function_schema() for t in tools]
