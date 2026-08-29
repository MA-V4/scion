from __future__ import annotations

from typing import Any


def compute_task_success(trace: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Binary: did the agent produce the expected outcome?"""
    # TODO: compare trace.final_answer against expected outputs
    raise NotImplementedError


def compute_tool_selection_accuracy(trace: dict[str, Any]) -> float:
    """Fraction of tool calls where the correct tool was selected."""
    # TODO: compare each tool call against expected_tool in the task definition
    raise NotImplementedError


def compute_step_count(trace: dict[str, Any]) -> int:
    return len(trace.get("steps", []))


def compute_token_count(trace: dict[str, Any]) -> int:
    return trace.get("total_tokens", 0)
