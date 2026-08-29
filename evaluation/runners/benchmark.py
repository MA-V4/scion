from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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
    tool_selection_accuracy: float
    trajectory_score: float
    judge_score: float | None = None
    error: str | None = None
    trace: dict[str, Any] = field(default_factory=dict)


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
    def mean_trajectory_score(self) -> float:
        scores = [o.trajectory_score for o in self.outcomes]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def tool_error_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        total_calls = sum(o.tool_calls_made for o in self.outcomes)
        if total_calls == 0:
            return 0.0
        # TODO: track invalid tool calls separately in TaskOutcome
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "run_at": self.run_at,
            "summary": {
                "task_success_rate": self.task_success_rate,
                "mean_trajectory_score": self.mean_trajectory_score,
                "tool_error_rate": self.tool_error_rate,
                "total_tasks": len(self.outcomes),
            },
            "outcomes": [vars(o) for o in self.outcomes],
        }


class BenchmarkRunner:
    """
    Loads tasks from YAML, runs each task through the agent, records outcomes.
    Results are written to benchmarks/results/ as JSON.
    """

    SUITE_PATHS = {
        "general": "evaluation/datasets/general/tasks.yaml",
        "scientific": "evaluation/datasets/scientific/tasks.yaml",
        "safety": "evaluation/datasets/safety/tasks.yaml",
    }

    def __init__(self, suite: str = "general") -> None:
        if suite not in self.SUITE_PATHS:
            raise ValueError(f"Unknown suite '{suite}'. Choose from: {list(self.SUITE_PATHS)}")
        self._suite = suite
        self._tasks: list[BenchmarkTask] = []

    def load_tasks(self) -> None:
        path = Path(self.SUITE_PATHS[self._suite])
        with open(path) as f:
            raw = yaml.safe_load(f)
        self._tasks = [BenchmarkTask(**t) for t in raw.get("tasks", [])]
        print(f"Loaded {len(self._tasks)} tasks from {path}")

    async def run(self) -> BenchmarkResult:
        result = BenchmarkResult(suite=self._suite)
        for task in self._tasks:
            print(f"  Running: {task.id}")
            outcome = await self._run_task(task)
            result.outcomes.append(outcome)

        self._save(result)
        return result

    async def _run_task(self, task: BenchmarkTask) -> TaskOutcome:
        # TODO:
        # 1. Instantiate AgentLoop with task.allowed_tools
        # 2. Run agent on task.description, capture AgentTrace
        # 3. Evaluate trace with DeterministicMetrics
        # 4. Score trajectory with TrajectoryScorer
        # 5. Optionally: score with LLMJudge
        # 6. Return TaskOutcome
        raise NotImplementedError

    def _save(self, result: BenchmarkResult) -> None:
        out = Path("benchmarks/results") / f"{self._suite}_{int(result.run_at)}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"Results written to {out}")
