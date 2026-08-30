from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import structlog

from evaluation.runners.benchmark import BenchmarkRunner

log = structlog.get_logger()

THRESHOLDS = {
    "task_success_rate": 0.80,
    "tool_error_rate_max": 0.20,
}


def load_baseline(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_baseline(result_path: str, baseline_path: str) -> None:
    src = Path(result_path)
    dst = Path(baseline_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text())
    log.info("ci.baseline_saved", path=str(dst))


async def run_ci(baseline_path: str, suite: str = "general") -> bool:
    runner = BenchmarkRunner(suite=suite)
    runner.load_tasks()
    result = await runner.run()
    result.print_summary()

    passed = True
    print("\nCI threshold checks:")

    if result.task_success_rate < THRESHOLDS["task_success_rate"]:
        print(
            f"  [FAIL] task_success_rate: {result.task_success_rate:.1%} < {THRESHOLDS['task_success_rate']:.1%}"
        )
        passed = False
    else:
        print(
            f"  [PASS] task_success_rate: {result.task_success_rate:.1%} >= {THRESHOLDS['task_success_rate']:.1%}"
        )

    if result.tool_error_rate > THRESHOLDS["tool_error_rate_max"]:
        print(
            f"  [FAIL] tool_error_rate: {result.tool_error_rate:.1%} > {THRESHOLDS['tool_error_rate_max']:.1%}"
        )
        passed = False
    else:
        print(
            f"  [PASS] tool_error_rate: {result.tool_error_rate:.1%} <= {THRESHOLDS['tool_error_rate_max']:.1%}"
        )

    baseline = load_baseline(baseline_path)
    if baseline:
        baseline_rate = baseline["summary"]["task_success_rate"]
        regression = baseline_rate - result.task_success_rate
        if regression > 0.10:
            print(
                f"  [FAIL] regression detected: {result.task_success_rate:.1%} vs baseline {baseline_rate:.1%} (dropped {regression:.1%})"
            )
            passed = False
        else:
            print(
                f"  [PASS] no regression: {result.task_success_rate:.1%} vs baseline {baseline_rate:.1%}"
            )
    else:
        print(f"  [INFO] no baseline found at {baseline_path}, saving current run as baseline")
        latest = sorted(Path("benchmarks/results").glob(f"{suite}_*.json"))[-1]
        save_baseline(str(latest), baseline_path)

    print(f"\nCI result: {'PASS' if passed else 'FAIL'}")
    return passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="benchmarks/results/baseline.json")
    parser.add_argument("--suite", default="general")
    args = parser.parse_args()

    passed = asyncio.run(run_ci(args.baseline, args.suite))
    sys.exit(0 if passed else 1)
