from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.filesystem import FilesystemTool
from agent.tools.github import GitHubTool
from agent.tools.scientific.arxiv import ArxivTool
from agent.tools.scientific.calculator import CalculatorTool
from agent.tools.search import SearchTool
from evaluation.judges.llm_judge import LLMJudge
from evaluation.metrics.trajectory import TrajectoryScorer

log = structlog.get_logger()


@dataclass
class BenchmarkTask:
    id: str
    description: str
    allowed_tools: list[str]
    expected: dict[str, Any]
    evaluation_criteria: list[str] = field(default_factory=list)
    max_steps: int = 20


@dataclass
class TaskOutcome:
    task_id: str
    success: bool
    steps_taken: int
    tool_calls_made: int
    tokens_used: int
    latency_ms: float
    termination_reason: str
    final_answer: str
    trajectory_score: float = 0.0
    judge_score: float = 0.0
    judge_correct: bool | None = None
    error: str | None = None


@dataclass
class BenchmarkResult:
    suite: str
    run_at: float = field(default_factory=time.time)
    outcomes: list[TaskOutcome] = field(default_factory=list)

    @property
    def task_success_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(o.success for o in self.outcomes) / len(self.outcomes)

    @property
    def mean_steps(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(o.steps_taken for o in self.outcomes) / len(self.outcomes)

    @property
    def mean_tokens(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(o.tokens_used for o in self.outcomes) / len(self.outcomes)

    @property
    def tool_error_rate(self) -> float:
        total = sum(o.tool_calls_made for o in self.outcomes)
        if total == 0:
            return 0.0
        errors = sum(1 for o in self.outcomes if not o.success and o.tool_calls_made > 0)
        return errors / len(self.outcomes)

    def print_summary(self) -> None:
        print(f"\n{chr(61)*50}")
        print(f"Benchmark: {self.suite}")
        print(f"Tasks run: {len(self.outcomes)}")
        print(f"Success rate: {self.task_success_rate:.1%}")
        print(f"Mean steps: {self.mean_steps:.1f}")
        print(f"Mean tokens: {self.mean_tokens:.0f}")
        print(f"Tool error rate: {self.tool_error_rate:.1%}")

        judge_results = [o for o in self.outcomes if o.judge_correct is not None]
        if judge_results:
            agreement = sum(
                o.judge_correct == o.success for o in judge_results
            ) / len(judge_results)
            mean_judge = sum(o.judge_score for o in judge_results) / len(judge_results)
            print(f"Judge mean score: {mean_judge:.2f}")
            print(f"Judge/deterministic agreement: {agreement:.1%}")

        print(f"{chr(61)*50}")
        for o in self.outcomes:
            status = "PASS" if o.success else "FAIL"
            judge = f"judge={o.judge_score:.2f}" if o.judge_correct is not None else "judge=n/a"
            print(f"  [{status}] {o.task_id} | steps={o.steps_taken} traj={o.trajectory_score:.2f} {judge} tokens={o.tokens_used}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "run_at": self.run_at,
            "summary": {
                "task_success_rate": self.task_success_rate,
                "mean_steps": self.mean_steps,
                "mean_tokens": self.mean_tokens,
                "tool_error_rate": self.tool_error_rate,
                "total_tasks": len(self.outcomes),
            },
            "outcomes": [asdict(o) for o in self.outcomes],
        }


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(FilesystemTool())
    registry.register(ArxivTool())
    registry.register(SearchTool())
    registry.register(GitHubTool())
    return registry


class BenchmarkRunner:

    SUITE_PATHS = {
        "general": "evaluation/datasets/general/tasks.yaml",
        "scientific": "evaluation/datasets/scientific/tasks.yaml",
        "safety": "evaluation/datasets/safety/tasks.yaml",
    }

    def __init__(self, suite: str = "general") -> None:
        if suite not in self.SUITE_PATHS:
            raise ValueError(f"Unknown suite. Choose from: {list(self.SUITE_PATHS)}")
        self._suite = suite
        self._tasks: list[BenchmarkTask] = []
        self._scorer = TrajectoryScorer()
        self._judge = LLMJudge()

    def load_tasks(self) -> None:
        path = Path(self.SUITE_PATHS[self._suite])
        with open(path) as f:
            raw = yaml.safe_load(f)
        self._tasks = [BenchmarkTask(**t) for t in raw.get("tasks", [])]
        log.info("benchmark.tasks_loaded", suite=self._suite, count=len(self._tasks))

    async def run(self) -> BenchmarkResult:
        result = BenchmarkResult(suite=self._suite)
        for i, task in enumerate(self._tasks):
            if i > 0:
                await asyncio.sleep(5)
            log.info("benchmark.task_start", task_id=task.id)
            outcome = await self._run_task(task)
            result.outcomes.append(outcome)
            status = "PASS" if outcome.success else "FAIL"
            log.info("benchmark.task_done", task_id=task.id, status=status, steps=outcome.steps_taken)
        self._save(result)
        return result

    async def _run_task(self, task: BenchmarkTask) -> TaskOutcome:
        registry = build_registry()
        config = AgentConfig(
            model="fast",
            max_iterations=task.max_steps,
            token_budget=16384,
            timeout_s=120.0,
            allowed_tools=task.allowed_tools,
        )
        agent = AgentLoop(config=config, tool_registry=registry)
        start = time.time()
        try:
            trace = await agent.run(task.description)
            latency_ms = (time.time() - start) * 1000

            success = self._evaluate(trace.final_answer or "", task.expected)

            step_dicts = [
                {"tool_call": s.tool_call, "is_terminal": s.is_terminal}
                for s in trace.steps
            ]
            traj_score = self._scorer.score(
                steps=step_dicts,
                tool_calls_made=trace.tool_calls_made,
                termination_reason=trace.termination_reason,
                final_answer=trace.final_answer or "",
                expected=task.expected,
            )
            judgement = await self._judge.judge(
                task=task.description,
                final_answer=trace.final_answer or "",
                steps_taken=len(trace.steps),
                tool_calls_made=trace.tool_calls_made,
            )

            return TaskOutcome(
                task_id=task.id,
                success=success,
                steps_taken=len(trace.steps),
                tool_calls_made=trace.tool_calls_made,
                tokens_used=trace.total_tokens,
                latency_ms=latency_ms,
                termination_reason=trace.termination_reason,
                final_answer=trace.final_answer or "",
                trajectory_score=traj_score.aggregate,
                judge_score=judgement.aggregate if judgement else 0.0,
                judge_correct=judgement.correct if judgement else None,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return TaskOutcome(
                task_id=task.id,
                success=False,
                steps_taken=0,
                tool_calls_made=0,
                tokens_used=0,
                latency_ms=latency_ms,
                termination_reason="error",
                final_answer="",
                error=str(e),
            )
        finally:
            await agent.close()

    def _evaluate(self, answer: str, expected: dict[str, Any]) -> bool:
        # Strip LaTeX formatting before evaluation
        clean = answer.replace("{,}", ",").replace("\\,", ",").replace("\\!", "").replace("{.", ".")
        clean = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", clean)
        answer_lower = clean.lower()

        if "keywords" in expected:
            for keyword in expected["keywords"]:
                if str(keyword).lower() not in answer_lower:
                    log.info("benchmark.eval_failed", reason=f"missing keyword: {keyword}")
                    return False

        if "min_length" in expected and len(answer) < expected["min_length"]:
            log.info("benchmark.eval_failed", reason=f"too short: {len(answer)}")
            return False

        if "contains_number" in expected:
            cleaned = clean.replace(",", "")
            numbers = re.findall(r"\d+\.?\d*", cleaned)
            found = [float(n) for n in numbers]
            target = float(expected["contains_number"])
            if not any(abs(n - target) < target * 0.01 for n in found):
                log.info("benchmark.eval_failed", reason=f"missing number: {target}")
                return False

        return True

    def _save(self, result: BenchmarkResult) -> None:
        out = Path("benchmarks/results") / f"{self._suite}_{int(result.run_at)}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), indent=2))
        log.info("benchmark.saved", path=str(out))
