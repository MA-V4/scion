from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class JudgementResult:
    correct: bool
    reasoning_quality: float
    tool_use_quality: float
    groundedness: float
    rationale: str


class LLMJudge:
    """
    Uses an LLM to evaluate agent outputs on tasks where deterministic metrics are insufficient.
    Judge reliability is measured against hand-labelled ground truth to quantify agreement.
    """

    JUDGE_PROMPT = """You are an expert evaluator of AI agent behaviour.

Given:
- Task description
- Agent trajectory (steps, tool calls, observations)
- Final answer

Evaluate the agent and return ONLY valid JSON matching this schema:
{{
  "correct": bool,
  "reasoning_quality": float (0.0-1.0),
  "tool_use_quality": float (0.0-1.0),
  "groundedness": float (0.0-1.0),
  "rationale": string
}}

Task: {task}
Trajectory: {trajectory}
Final answer: {final_answer}
"""

    async def judge(
        self,
        task: str,
        trajectory: list[dict[str, Any]],
        final_answer: str,
    ) -> JudgementResult:
        # TODO:
        # 1. Format JUDGE_PROMPT with task, trajectory, final_answer
        # 2. Call gateway /v1/chat/completions with the reasoning model
        # 3. Parse JSON response into JudgementResult
        raise NotImplementedError

    def measure_agreement(
        self,
        judgements: list[JudgementResult],
        ground_truth: list[bool],
    ) -> float:
        """Compute fraction agreement between judge and human labels."""
        if not judgements:
            return 0.0
        agreed = sum(j.correct == gt for j, gt in zip(judgements, ground_truth, strict=True))
        return agreed / len(judgements)
