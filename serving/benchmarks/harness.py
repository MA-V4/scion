from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class BenchmarkConfig:
    target_url: str = "http://localhost:8000"
    model: str = "fast"
    concurrency_levels: list[int] = field(default_factory=lambda: [1, 2, 4, 8, 16, 32])
    requests_per_level: int = 50
    prompt_short: str = "What is 2 + 2?"
    prompt_medium: str = "Explain how transformers work in 200 words."
    prompt_long: str = "Write a detailed essay on the history of machine learning." * 3


@dataclass
class BenchmarkResult:
    concurrency: int
    prompt_type: str
    requests_completed: int
    ttft_p50_ms: float
    ttft_p95_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    tokens_per_sec: float
    requests_per_sec: float
    error_rate: float


class BenchmarkHarness:
    """
    Inference throughput benchmark harness.
    Varies concurrency and prompt length, records TTFT, TPOT, latency, and throughput.
    """

    def __init__(self, config: BenchmarkConfig) -> None:
        self._config = config
        self._results: list[BenchmarkResult] = []

    async def run(self) -> list[BenchmarkResult]:
        for concurrency in self._config.concurrency_levels:
            for prompt_type, prompt in [
                ("short", self._config.prompt_short),
                ("medium", self._config.prompt_medium),
                ("long", self._config.prompt_long),
            ]:
                result = await self._run_level(concurrency, prompt_type, prompt)
                self._results.append(result)
                print(f"  concurrency={concurrency} prompt={prompt_type} -> p95={result.latency_p95_ms:.0f}ms tps={result.tokens_per_sec:.1f}")

        return self._results

    async def _run_level(self, concurrency: int, prompt_type: str, prompt: str) -> BenchmarkResult:
        # TODO: implement concurrent request dispatch with timing collection
        # Collect: TTFT per request, total latency, token counts
        # Compute percentiles and aggregates
        raise NotImplementedError
