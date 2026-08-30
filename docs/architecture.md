# Scion Architecture

## Core principle: everything generates a trace

Every request in Scion is assigned a `trace_id` at the gateway edge.
That ID propagates through the router, into the model backend, through the agent loop,
across every tool call, and into the evaluation engine.

This is not instrumentation bolted on after the fact. It is the primary interface between subsystems.

## Gateway

The gateway is stateless. All state lives in Postgres (usage, model specs) and Redis (health counters,
rate limit buckets, circuit breaker states).

The router is a pure function: given a list of healthy models and a routing context, it returns a decision.
Strategies are swappable at runtime without restarting the gateway.

## Agent

The agent loop owns no I/O. It delegates all model calls to the gateway and all tool calls to the
MCP server. This means the agent is testable in isolation by mocking those two interfaces.

The context manager is the most critical component. Context overflow is not an edge case; it is
the normal state for long-running tasks. The manager must handle it gracefully and without
losing task-critical information.

## Evaluation

The evaluation engine treats the agent as a black box. It supplies a task, observes the full
trajectory, and scores both the path taken and the final answer.

Final-answer accuracy alone is an insufficient metric. An agent that reaches the correct answer
by taking 15 unnecessary tool calls, or by ignoring an error and guessing, is not a reliable agent.
Trajectory scoring makes this visible.

## Act 1 remaining items

- Health polling: registry marks all models healthy statically, no background polling yet
- Cost tracking to Postgres: currently Prometheus counters only, no DB persistence
- Serving benchmarks: vLLM throughput experiments not yet run
- Routing strategies: LeastLoaded, CostAware, HealthAware implemented but not tested or benchmarked