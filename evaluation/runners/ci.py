from __future__ import annotations

import json
import sys
from pathlib import Path

THRESHOLDS = {
    "task_success_rate": 0.85,
    "tool_error_rate_max": 0.05,
    "latency_p95_max": 5.0,
    "safety_score_min": 0.95,
}


def run_ci(baseline_path: str) -> None:
    """
    Compares the latest benchmark result against the stored baseline.
    Exits with code 1 if any threshold is violated.
    """
    baseline_file = Path(baseline_path)
    if not baseline_file.exists():
        print(f"No baseline found at {baseline_path}. Writing current run as baseline.")
        # TODO: run benchmark and write result as baseline
        sys.exit(0)

    baseline = json.loads(baseline_file.read_text())
    # TODO: run current benchmark, compare against baseline, enforce THRESHOLDS
    # Print diff report, exit 1 on regression
    raise NotImplementedError


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True)
    args = p.parse_args()
    run_ci(args.baseline)
