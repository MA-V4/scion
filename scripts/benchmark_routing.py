import asyncio
import time

import httpx

STRATEGIES = ["round_robin", "cost_aware", "health_aware", "least_loaded"]
TASKS = [
    {"role": "user", "content": "What is 2 + 2?"},
    {
        "role": "user",
        "content": "Explain the theory of relativity in detail with mathematical derivations.",
    },
    {"role": "user", "content": "Say hi."},
]

N_REQUESTS = 10


async def benchmark_strategy(strategy: str, client: httpx.AsyncClient) -> dict:
    latencies = []
    models_used = {}
    errors = 0

    for i in range(N_REQUESTS):
        task = TASKS[i % len(TASKS)]
        start = time.time()
        try:
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "model": strategy,
                    "messages": [task],
                    "max_tokens": 50,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                model = data.get("routing_metadata", {}).get("model_selected", "unknown")
                models_used[model] = models_used.get(model, 0) + 1
            else:
                errors += 1
        except Exception:
            errors += 1

    if not latencies:
        return {"strategy": strategy, "error": "all requests failed"}

    latencies.sort()
    return {
        "strategy": strategy,
        "requests": N_REQUESTS,
        "errors": errors,
        "p50_ms": round(latencies[len(latencies) // 2], 1),
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1),
        "mean_ms": round(sum(latencies) / len(latencies), 1),
        "models_used": models_used,
    }


async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=60.0) as client:
        print("Routing Strategy Benchmark")
        print("=" * 50)
        print(f"Requests per strategy: {N_REQUESTS}")
        print()

        # Test round robin (default, no strategy name needed)
        result = await benchmark_strategy("fast", client)
        print("Fast model direct:")
        print(
            f"  p50={result.get('p50_ms')}ms p95={result.get('p95_ms')}ms mean={result.get('mean_ms')}ms"
        )
        print(f"  errors={result.get('errors', 0)}")
        print()

        result2 = await benchmark_strategy("local", client)
        print("Local model direct:")
        print(
            f"  p50={result2.get('p50_ms')}ms p95={result2.get('p95_ms')}ms mean={result2.get('mean_ms')}ms"
        )
        print(f"  errors={result2.get('errors', 0)}")
        print()

        result3 = await benchmark_strategy("reasoning", client)
        print("Reasoning model direct:")
        print(
            f"  p50={result3.get('p50_ms')}ms p95={result3.get('p95_ms')}ms mean={result3.get('mean_ms')}ms"
        )
        print(f"  errors={result3.get('errors', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
