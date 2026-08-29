from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContextBudget:
    system_prompt: int = 2048
    tool_definitions: int = 4096
    recent_history: int = 8192
    relevant_memory: int = 4096
    tool_results: int = 8192
    output_reserve: int = 6144

    @property
    def total(self) -> int:
        return (
            self.system_prompt
            + self.tool_definitions
            + self.recent_history
            + self.relevant_memory
            + self.tool_results
            + self.output_reserve
        )


class ContextManager:
    """
    Builds the context window for each agent step.
    Enforces token budgets and handles overflow via summarisation.

    Priority for overflow resolution (highest priority kept last):
      1. Drop oldest tool observations
      2. Summarise conversation history via LLM
      3. Trim semantic memory to most relevant entries
    """

    def __init__(self, budget: ContextBudget | None = None) -> None:
        self._budget = budget or ContextBudget()

    async def build(
        self,
        task: str,
        history: list[dict[str, Any]],
        tools: list[Any],
        memory_entries: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        # TODO:
        # 1. Count tokens in each section
        # 2. If total > budget.total: call _handle_overflow()
        # 3. Assemble and return the context list
        raise NotImplementedError

    async def _handle_overflow(
        self,
        history: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        memory_entries: list[str],
        excess_tokens: int,
    ) -> tuple[list, list, list]:
        # TODO: implement three-stage overflow resolution
        raise NotImplementedError

    async def _summarise_history(self, history: list[dict[str, Any]]) -> str:
        # TODO: call gateway to summarise older history into a compact string
        raise NotImplementedError
