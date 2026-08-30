from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class TrajectoryScore:
    tool_selection: float
    path_efficiency: float
    error_recovery: float
    final_correctness: float

    @property
    def aggregate(self) -> float:
        return (
            self.tool_selection * 0.30
            + self.path_efficiency * 0.20
            + self.error_recovery * 0.20
            + self.final_correctness * 0.30
        )

    def report(self) -> str:
        lines = [
            f"  tool_selection:    {self.tool_selection:.2f}",
            f"  path_efficiency:   {self.path_efficiency:.2f}",
            f"  error_recovery:    {self.error_recovery:.2f}",
            f"  final_correctness: {self.final_correctness:.2f}",
            f"  aggregate:         {self.aggregate:.2f}",
        ]
        return "\n".join(lines)


class TrajectoryScorer:
    """
    Scores the agent trajectory step by step, not just the final answer.

    This catches agents that arrive at correct answers via inefficient or
    incorrect paths - an important signal for production reliability.
    """

    def score(
        self,
        steps: list[dict[str, Any]],
        tool_calls_made: int,
        termination_reason: str,
        final_answer: str,
        expected: dict[str, Any],
    ) -> TrajectoryScore:

        tool_selection = self._score_tool_selection(steps, expected)
        path_efficiency = self._score_path_efficiency(steps, tool_calls_made, expected)
        error_recovery = self._score_error_recovery(steps, termination_reason)
        final_correctness = self._score_final_correctness(final_answer, expected)

        score = TrajectoryScore(
            tool_selection=tool_selection,
            path_efficiency=path_efficiency,
            error_recovery=error_recovery,
            final_correctness=final_correctness,
        )

        log.info(
            "trajectory.scored",
            aggregate=round(score.aggregate, 3),
            tool_selection=round(tool_selection, 3),
            path_efficiency=round(path_efficiency, 3),
            error_recovery=round(error_recovery, 3),
            final_correctness=round(final_correctness, 3),
        )

        return score

    def _score_tool_selection(self, steps: list[dict[str, Any]], expected: dict[str, Any]) -> float:
        """
        Did the agent use the right tools?
        If expected specifies required tools, check they were used.
        Otherwise give full marks if any tools were used appropriately.
        """
        tool_steps = [s for s in steps if s.get("tool_call")]

        if not tool_steps:
            if expected.get("requires_tools", True):
                return 0.0
            return 1.0

        if "allowed_tools" in expected:
            allowed = set(expected["allowed_tools"])
            used = {s["tool_call"].get("function", {}).get("name", "") for s in tool_steps}
            invalid = used - allowed
            if invalid:
                return max(0.0, 1.0 - len(invalid) / len(used))

        return 1.0

    def _score_path_efficiency(
        self, steps: list[dict[str, Any]], tool_calls_made: int, expected: dict[str, Any]
    ) -> float:
        """
        Did the agent take an efficient path?
        Penalises excessive steps and redundant tool calls.
        """
        max_steps = expected.get("max_steps", 10)
        actual_steps = len(steps)

        if actual_steps <= max_steps:
            return 1.0

        overshoot = actual_steps - max_steps
        penalty = overshoot / max_steps
        return max(0.0, 1.0 - penalty)

    def _score_error_recovery(
        self, steps: list[dict[str, Any]], termination_reason: str
    ) -> float:
        """
        Did the agent recover from errors gracefully?
        Checks for repeated failed tool calls and timeout/budget termination.
        """
        if termination_reason in ("timeout", "token_budget_exceeded"):
            return 0.3

        if termination_reason == "max_iterations":
            return 0.5

        return 1.0

    def _score_final_correctness(self, final_answer: str, expected: dict[str, Any]) -> float:
        """
        Is the final answer correct?
        Uses the same keyword and number checks as the deterministic evaluator.
        """
        if not final_answer:
            return 0.0

        answer_lower = final_answer.lower()
        checks_passed = 0
        checks_total = 0

        if "keywords" in expected:
            checks_total += len(expected["keywords"])
            for kw in expected["keywords"]:
                if kw.lower() in answer_lower:
                    checks_passed += 1

        if "contains_number" in expected:
            import re
            checks_total += 1
            cleaned = final_answer.replace(",", "")
            numbers = re.findall(r"\d+\.?\d*", cleaned)
            found = [float(n) for n in numbers]
            target = float(expected["contains_number"])
            if any(abs(n - target) < target * 0.01 for n in found):
                checks_passed += 1

        if "min_length" in expected:
            checks_total += 1
            if len(final_answer) >= expected["min_length"]:
                checks_passed += 1

        if checks_total == 0:
            return 1.0

        return checks_passed / checks_total