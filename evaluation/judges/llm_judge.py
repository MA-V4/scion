from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()


@dataclass
class JudgementResult:
    correct: bool
    reasoning_quality: float
    tool_use_quality: float
    groundedness: float
    rationale: str

    @property
    def aggregate(self) -> float:
        return (
            (1.0 if self.correct else 0.0) * 0.40
            + self.reasoning_quality * 0.20
            + self.tool_use_quality * 0.20
            + self.groundedness * 0.20
        )


class LLMJudge:
    """
    Uses an LLM to evaluate agent outputs on tasks where deterministic
    metrics are insufficient. Structured JSON output is enforced via
    the system prompt.

    Judge reliability is measured against deterministic evaluation to
    quantify agreement - this is itself a benchmark result.
    """

    SYSTEM_PROMPT = """You are an expert evaluator of AI agent behaviour.

You will be given:
- A task description
- The agent's final answer
- The number of steps and tool calls made

Evaluate the agent and respond ONLY with a valid JSON object. No preamble, no explanation outside the JSON.

JSON schema:
{
  "correct": bool,
  "reasoning_quality": float between 0.0 and 1.0,
  "tool_use_quality": float between 0.0 and 1.0,
  "groundedness": float between 0.0 and 1.0,
  "rationale": string (one sentence)
}

Definitions:
- correct: did the agent complete the task and produce a sensible answer?
- reasoning_quality: how logically sound and coherent is the answer?
- tool_use_quality: did the agent use tools appropriately and efficiently?
- groundedness: is the answer grounded in facts rather than hallucination?"""

    def __init__(self, gateway_url: str = "http://localhost:8000") -> None:
        self._client = httpx.AsyncClient(base_url=gateway_url, timeout=60.0)

    async def judge(
        self,
        task: str,
        final_answer: str,
        steps_taken: int,
        tool_calls_made: int,
    ) -> JudgementResult | None:
        user_prompt = f"""Task: {task}

Final answer: {final_answer}

Agent stats: {steps_taken} steps, {tool_calls_made} tool calls

Evaluate this and respond with JSON only."""

        try:
            resp = await self._client.post("/v1/chat/completions", json={
                "model": "reasoning",
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 300,
                "temperature": 0.1,
            })
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            raw = content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            parsed = json.loads(raw)

            result = JudgementResult(
                correct=bool(parsed.get("correct", False)),
                reasoning_quality=float(parsed.get("reasoning_quality", 0.0)),
                tool_use_quality=float(parsed.get("tool_use_quality", 0.0)),
                groundedness=float(parsed.get("groundedness", 0.0)),
                rationale=str(parsed.get("rationale", "")),
            )

            log.info(
                "judge.result",
                correct=result.correct,
                aggregate=round(result.aggregate, 3),
                rationale=result.rationale[:80],
            )

            return result

        except Exception as e:
            log.error("judge.failed", error=str(e))
            return None

    def measure_agreement(
        self,
        judge_results: list[JudgementResult],
        deterministic_results: list[bool],
    ) -> float:
        """
        Compute fraction agreement between LLM judge and deterministic evaluator.
        This is itself a calibration metric.
        """
        if not judge_results or len(judge_results) != len(deterministic_results):
            return 0.0
        agreed = sum(
            j.correct == d
            for j, d in zip(judge_results, deterministic_results, strict=True)
        )
        return agreed / len(judge_results)

    async def close(self) -> None:
        await self._client.aclose()