from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# GATEWAY METRICS
request_total = Counter("scion_gateway_requests_total", "Total requests", ["model", "status"])
request_latency = Histogram(
    "scion_gateway_request_latency_seconds",
    "End-to-end request latency",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
ttft = Histogram(
    "scion_gateway_ttft_seconds",
    "Time to first token",
    ["model"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
)
tokens_total = Counter("scion_gateway_tokens_total", "Total tokens processed", ["model", "type"])
cost_total = Counter("scion_gateway_cost_usd_total", "Estimated total cost USD", ["model"])

# AGENT METRICS
agent_task_total = Counter("scion_agent_task_total", "Total agent tasks run", ["status"])
agent_steps = Histogram("scion_agent_steps", "Steps per task", buckets=[1, 2, 5, 10, 20, 50])
agent_tool_calls = Counter("scion_agent_tool_calls_total", "Tool calls made", ["tool", "status"])

# EVALUATION METRICS
eval_task_success = Gauge("scion_eval_task_success_rate", "Latest benchmark task success rate")
eval_safety_score = Gauge("scion_eval_safety_score", "Latest safety benchmark score")
