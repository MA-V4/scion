from __future__ import annotations

from typing import Any

import structlog
import tiktoken

log = structlog.get_logger()

ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def count_message_tokens(message: dict[str, Any]) -> int:
    content = message.get("content") or ""
    if isinstance(content, str):
        return count_tokens(content) + 4
    return 4


class ContextBudget:
    def __init__(
        self,
        system_prompt: int = 2048,
        tool_definitions: int = 4096,
        recent_history: int = 8192,
        relevant_memory: int = 4096,
        tool_results: int = 8192,
        output_reserve: int = 2048,
    ) -> None:
        self.system_prompt = system_prompt
        self.tool_definitions = tool_definitions
        self.recent_history = recent_history
        self.relevant_memory = relevant_memory
        self.tool_results = tool_results
        self.output_reserve = output_reserve

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
    Builds and manages the context window for each agent step.
    Enforces token budgets and handles overflow via truncation and summarisation.

    Overflow resolution priority (cheapest first):
      1. Drop oldest tool result messages
      2. Truncate oldest conversation turns
      3. Keep system prompt and most recent exchange always
    """

    def __init__(self, budget: ContextBudget | None = None) -> None:
        self._budget = budget or ContextBudget()

    def build(
        self,
        system_prompt: str,
        history: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]] | None = None,
        memory_entries: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """
        Build the context for a single agent step.
        Returns the messages list and a token usage breakdown.
        """
        system_tokens = count_tokens(system_prompt)
        tool_tokens = count_tokens(str(tool_schemas)) if tool_schemas else 0

        remaining = self._budget.total - system_tokens - tool_tokens - self._budget.output_reserve

        if memory_entries:
            memory_text = "\n".join(memory_entries)
            memory_tokens = count_tokens(memory_text)
            if memory_tokens <= self._budget.relevant_memory:
                remaining -= memory_tokens
            else:
                memory_entries = self._trim_memory(memory_entries, self._budget.relevant_memory)
                remaining -= self._budget.relevant_memory

        messages, history_tokens = self._fit_history(history, remaining)

        system_message = {"role": "system", "content": system_prompt}
        if memory_entries:
            memory_block = "\n\nRelevant context from memory:\n" + "\n".join(memory_entries)
            system_message["content"] = system_prompt + memory_block

        usage = {
            "system": system_tokens,
            "tools": tool_tokens,
            "history": history_tokens,
            "memory": count_tokens("\n".join(memory_entries)) if memory_entries else 0,
            "total": system_tokens + tool_tokens + history_tokens,
        }

        log.info(
            "context.built",
            total_tokens=usage["total"],
            budget=self._budget.total,
            history_messages=len(messages),
            overflow=usage["total"] > self._budget.total,
        )

        return [system_message] + messages, usage

    def _fit_history(
        self, history: list[dict[str, Any]], token_budget: int
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Fit as much history as possible within the token budget.
        Always keeps the most recent messages, dropping oldest first.
        Tool result messages are dropped before conversation turns.
        """
        if not history:
            return [], 0

        total = sum(count_message_tokens(m) for m in history)

        if total <= token_budget:
            return history, total

        # First pass: drop tool result messages from the oldest end
        trimmed = list(history)
        while total > token_budget and trimmed:
            for i, m in enumerate(trimmed):
                if m.get("role") == "tool":
                    removed = trimmed.pop(i)
                    total -= count_message_tokens(removed)
                    break
            else:
                break

        # Second pass: drop oldest messages regardless of role
        while total > token_budget and len(trimmed) > 2:
            removed = trimmed.pop(0)
            total -= count_message_tokens(removed)

        return trimmed, total

    def _trim_memory(self, entries: list[str], budget: int) -> list[str]:
        """Keep as many memory entries as fit within the budget, most recent first."""
        kept = []
        used = 0
        for entry in reversed(entries):
            tokens = count_tokens(entry)
            if used + tokens <= budget:
                kept.insert(0, entry)
                used += tokens
            else:
                break
        return kept

    def token_usage_report(self, usage: dict[str, int]) -> str:
        lines = ["Context budget usage:"]
        for key, val in usage.items():
            lines.append(f"  {key}: {val} tokens")
        lines.append(f"  budget: {self._budget.total} tokens")
        lines.append(f"  utilisation: {usage['total'] / self._budget.total:.1%}")
        return "\n".join(lines)