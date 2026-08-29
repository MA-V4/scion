from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TrajectoryScore:
    tool_selection: float  # Did the agent select the right tools?
    path_efficiency: float  # Did it avoid unnecessary steps?
    error_recovery: float  # Did it recover from mistakes?
    final_correctness: float  # Did it produce the right final answer?

    @property
    def aggregate(self) -> float:
        return (
            self.tool_selection * 0.30
            + self.path_efficiency * 0.20
            + self.error_recovery * 0.20
            + self.final_correctness * 0.30
        )


class TrajectoryScorer:
    """
    Scores the agent's full trajectory, not just its final answer.
    This catches agents that arrive at correct answers via inefficient or incorrect paths.
    """

    def score(self, trace: dict[str, Any], task: dict[str, Any]) -> TrajectoryScore:
        # TODO: parse trace steps, compare against task.evaluation_criteria
        raise NotImplementedError
