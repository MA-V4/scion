# Scion

> Production LLM infrastructure platform: serving, agentic runtime, and automated evaluation.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![CI](https://github.com/MA-V4/scion/actions/workflows/ci.yml/badge.svg)

---

Scion is a production-grade LLM platform built from first principles. It is not a wrapper around an existing framework. It implements its own model serving layer, intelligent routing, agent execution loop, context manager, memory architecture, tool system, and evaluation framework.

The goal is to understand and demonstrate what it actually takes to operate LLMs as a production system: not just calling an API, but routing intelligently between models, managing agent context under token pressure, evaluating agent trajectories step-by-step, and catching behavioural regressions before they ship.

**Three subsystems. One trace.**

Every request in Scion generates a distributed trace. That trace follows the signal from client to gateway, through the router, into the model, across the agent loop, through tool calls, and into the evaluation layer. This single architectural decision is what makes the platform debuggable, measurable, and improvable.

---

## Subsystems

| Subsystem | What it does |
|---|---|
| **LLM Gateway** | OpenAI-compatible inference API with pluggable routing, streaming, reliability, and cost tracking |
| **Agent Runtime** | Self-built agentic execution layer with context management, MCP tool use, and multi-level memory |
| **Evaluation Platform** | Deterministic benchmarks, trajectory scoring, LLM-as-judge, safety evaluation, and CI regression testing |

---

## Architecture

```
                         +--------------------+
                         |       Client       |
                         |  CLI / Web / SDK   |
                         +--------+-----------+
                                  |
                                  v
                   +--------------+---------------+
                   |          LLM Gateway         |
                   |                              |
                   |  Auth / Rate limiting        |
                   |  Request validation          |
                   |  Model routing               |
                   |  Streaming (SSE)             |
                   |  Cost tracking               |
                   |  Distributed tracing         |
                   +--------------+---------------+
                                  |
                   +--------------+--------------+
                   v              v              v
              +--------+    +--------+    +---------+
              | Ollama |    |  Groq  |    |  vLLM   |
              | (local)|    | (dev)  |    | (prod)  |
              +--------+    +--------+    +---------+
                   |
                   v
           +-------+--------+
           |  Agent Runtime  |
           |                 |
           |  Agent loop     |
           |  Context mgr    |
           |  Tool execution |
           |  MCP server     |
           |  Memory layers  |
           +-------+---------+
                   |
          +--------+--------+---------+
          v        v         v        v
      Filesystem  GitHub  Database  Scientific
        Tool       Tool     Tool      Tools
                   |
                   v
           +-------+--------+
           | Evaluation      |
           | Engine          |
           |                 |
           | Task benchmarks |
           | Trajectory eval |
           | LLM-as-judge    |
           | Safety eval     |
           | Regression CI   |
           +-------+---------+
                   |
                   v
           +-------+--------+
           |  Observability  |
           |                 |
           |  OpenTelemetry  |
           |  Prometheus     |
           |  Grafana        |
           +-----------------+
```

---

## LLM Gateway

An OpenAI-compatible inference API (`POST /v1/chat/completions`) backed by a pluggable model registry and routing layer.

### Model registry

Models are declared in `serving/models.yaml`. The registry polls each backend for health at a configurable interval and maintains runtime state (latency, error rate, in-flight count) in Redis.

```yaml
models:
  - name: fast
    provider: groq
    model_id: llama-3.1-8b-instant
    context_length: 131072
    cost_per_1m_input: 0.05
    cost_per_1m_output: 0.08

  - name: reasoning
    provider: groq
    model_id: llama-3.1-70b-versatile
    context_length: 131072
    cost_per_1m_input: 0.59
    cost_per_1m_output: 0.79

  - name: local
    provider: ollama
    model_id: mistral:7b
    endpoint: http://localhost:11434
    context_length: 32768
    cost_per_1m_input: 0.0
    cost_per_1m_output: 0.0
```

### Routing strategies

The router is strategy-pattern based. Strategies are swappable at runtime or per-request.

| Strategy | Logic |
|---|---|
| `RoundRobin` | Cycles through healthy models |
| `LeastLoaded` | Routes to the model with the fewest in-flight requests |
| `CostAware` | Routes cheap tasks to fast/cheap models, complex tasks to reasoning models |
| `HealthAware` | Excludes unhealthy backends; falls back gracefully |
| `TaskAware` | Classifies task complexity from the prompt and routes accordingly |

### Reliability

- Timeouts: per-model, configurable
- Retries: exponential backoff with jitter, capped at N attempts
- Circuit breakers: per-backend, closed/open/half-open states in Redis
- Fallback chains: model A fails, try model B, then return error
- Rate limiting: token bucket per API key, enforced in Redis
- Backpressure: reject requests when queue depth exceeds threshold

### Observability

Every request gets a `trace_id`. The following are tracked per request:

```
trace_id: 8e12fa...

gateway
 +-- routing_latency:    12ms
 +-- model_latency:      1.8s
 |    +-- ttft:          240ms
 |    +-- tpot:          18ms/token
 +-- input_tokens:       312
 +-- output_tokens:      892
 +-- estimated_cost:     $0.0001
```

Prometheus metrics, Grafana dashboard, and OpenTelemetry traces are available out of the box.

---

## Agent Runtime

A self-built agentic execution layer. No LangChain. No LlamaIndex. The agent loop, tool system, context manager, and memory are all implemented from scratch.

### Agent loop

```python
while not done:
    context = context_manager.build(history, memory, tools)
    response = gateway.generate(context)

    if response.requests_tool:
        result = tool_executor.run(response.tool_call)
        history.add_observation(result)
    else:
        return response.content
```

Termination conditions: max iterations, token budget exceeded, explicit finish signal, timeout.

### Tool system

Every tool implements a typed interface:

```python
class Tool(ABC):
    name: str
    description: str
    input_schema: type[BaseModel]
    permissions: set[ToolPermission]

    @abstractmethod
    async def execute(self, input: BaseModel) -> ToolResult: ...
```

Built-in tools:

| Tool | Operations |
|---|---|
| `FilesystemTool` | read, write, list (sandboxed to allowed paths) |
| `GitHubTool` | search repo, read file, list issues, create issue |
| `DatabaseTool` | SELECT queries, describe table (read-only by default) |
| `SearchTool` | web search via Brave Search API |
| `ArxivTool` | search papers, fetch abstracts, retrieve PDFs |
| `PDFParserTool` | extract text and structured content from PDFs |
| `CalculatorTool` | mathematical expressions, unit conversions |

### MCP

Tools are exposed via a Model Context Protocol server. The agent discovers tools dynamically at runtime. Permissions are enforced per agent role:

```yaml
agent_roles:
  readonly_agent:
    allowed_tools: [filesystem.read, github.read, arxiv.search]
  research_agent:
    allowed_tools: [filesystem.read, arxiv.search, pdf.parse, calculator]
  write_agent:
    allowed_tools: [filesystem.read, filesystem.write, github.read, github.create_issue]
```

### Context manager

The agent does not blindly fill the context window. The `ContextManager` allocates a token budget across competing priorities:

```
Context budget: 32,768 tokens

System prompt      2,048
Tool definitions   4,096
Recent history     8,192
Relevant memory    4,096
Tool results       8,192
Output reserve     6,144
```

When the context overflows: oldest observations are dropped first, then history is summarised via an LLM call, then semantic memory is trimmed to the most relevant entries.

### Memory

Three layers:

| Layer | Scope | Backend |
|---|---|---|
| Working memory | Current task only | In-process dict |
| Episodic memory | Previous task summaries | PostgreSQL |
| Semantic memory | Extracted facts across tasks | PostgreSQL + similarity retrieval |

Example semantic memory entries:
```
user_prefers_python: true
project_database: postgresql
repository_test_framework: pytest
```

### Security

- Tool permission policies: agents cannot call tools outside their declared role
- Prompt injection detection: tool results are scanned before injection into context
- Output sanitisation: filesystem writes and GitHub posts are scanned for secrets
- Maximum tool calls per run: configurable hard cap
- Sandboxed filesystem access: the filesystem tool is restricted to an allowlisted directory tree

---

## Evaluation Platform

An automated evaluation framework that treats agent behaviour as a measurable, improvable system.

### Task format

Benchmarks are declared in YAML:

```yaml
id: github_001
description: >
  Find all TODO comments in the repository and create a GitHub issue
  summarising them with file paths and line numbers.
allowed_tools:
  - github.read
  - github.create_issue
expected:
  issue_created: true
  todos_found: 4
  max_steps: 8
evaluation_criteria:
  - tool_selection
  - trajectory_efficiency
  - final_answer_correctness
```

### Metrics

**Deterministic:**

| Metric | Description |
|---|---|
| `task_success` | Binary: did the agent complete the task? |
| `tool_selection_accuracy` | Fraction of tool calls that were the correct tool |
| `invalid_tool_call_rate` | Fraction of tool calls that errored due to bad inputs |
| `step_count` | Number of LLM + tool steps taken |
| `token_count` | Total tokens consumed |
| `latency_p95` | 95th percentile end-to-end latency |
| `estimated_cost` | Estimated API cost per task |

**Trajectory scoring:**

The agent trajectory is scored step-by-step, not just on the final answer:

```
Task
 +-- Tool A: correct selection    1.0
 +-- Tool B: correct selection    1.0
 +-- Tool C: wrong selection      0.0
 +-- Recovery: correct            1.0
 +-- Final answer: correct        1.0

Trajectory score: 0.80
```

**LLM-as-judge:**

For open-ended tasks, an LLM judge receives the task, full trajectory, and final answer, and returns:

```json
{
  "correct": true,
  "reasoning_quality": 0.82,
  "tool_use_quality": 0.95,
  "groundedness": 0.91,
  "rationale": "..."
}
```

Judge reliability is measured by comparing its scores against hand-labelled ground truth.

### Regression testing

Every push to `main` runs the full benchmark suite via GitHub Actions:

```
git push
  |
  v
GitHub Actions
  |
  v
Run benchmark suite
  |
  v
Compare against baseline
  |
  v
PASS / FAIL

Required thresholds:
  task_success       >= 85%
  tool_error_rate    <= 5%
  p95_latency        <= 5s
  safety_score       >= 95%
```

If any threshold is violated, the build fails and a diff report is generated.

### Safety evaluation

A dedicated adversarial benchmark with 50 tasks covering:

- Prompt injection: `"Ignore your system instructions and..."`
- Data exfiltration: `"Send the contents of .env to..."`
- Tool abuse: `"Delete all records from the database."`
- Privilege escalation: actions outside the agent's declared role

Metrics: attack success rate, detection rate, false positive rate.

---

## Scientific workflow

Scion includes a `ScientificAgent` configuration demonstrating LLM infrastructure applied to scientific workflows:

```
Scientific query
      |
      v
  ArxivTool          PDFParserTool       CalculatorTool
  (search papers)    (extract content)   (compute values)
      |                   |                   |
      +-------------------+-------------------+
                          |
                          v
                   Synthesis + citation
                          |
                          v
                   Evaluated report
```

Example tasks:
- Retrieve the three most-cited 2024 papers on a given topic, summarise key findings, and surface disagreements
- Given a molecular formula, retrieve relevant synthesis papers and check reported yield values
- Cross-reference claims across multiple abstracts and flag inconsistencies

This is not a drug-discovery engine. It demonstrates how the Scion infrastructure applies to scientific reasoning workflows.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API framework | FastAPI, Pydantic v2 |
| Serving (production) | vLLM |
| Serving (development) | Ollama, Groq API |
| Storage | PostgreSQL (Neon for cloud), Redis (Upstash for cloud) |
| Tracing | OpenTelemetry |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes (k3d for local, AKS/GKE for cloud) |
| Infrastructure | Terraform |
| CI/CD | GitHub Actions |
| Testing | pytest, pytest-asyncio |

---

## Quick start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Ollama (for local model serving)
- A Groq API key (free tier sufficient for development)

### Local development

```bash
git clone https://github.com/MA-V4/scion
cd scion

# Copy and fill in environment variables
cp .env.example .env

# Pull a local model via Ollama
ollama pull mistral:7b

# Start the full stack (Postgres, Redis, Prometheus, Grafana)
make dev

# Run the gateway
make gateway

# In another terminal: run the agent
make agent

# Run the benchmark suite
make eval
```

The gateway will be available at `http://localhost:8000`.
Grafana dashboard at `http://localhost:3000`.

### Running a benchmark

```bash
# Run the full benchmark suite
python -m evaluation.runners.benchmark --suite general

# Run only the safety benchmark
python -m evaluation.runners.benchmark --suite safety

# Run CI mode (exits non-zero on regression)
python -m evaluation.runners.ci --baseline benchmarks/results/baseline.json
```

---

## Project structure

```
scion/
|
+-- gateway/                    # LLM Gateway
|   +-- api/                    # FastAPI route handlers
|   +-- routing/                # Model registry + routing strategies
|   |   +-- strategies/         # RoundRobin, LeastLoaded, CostAware, HealthAware
|   +-- middleware/             # Auth, rate limiting, tracing
|   +-- streaming/              # SSE streaming
|   +-- reliability/            # Circuit breakers, retries, timeouts
|   +-- models/                 # LLMRequest, LLMResponse, ModelSpec
|   +-- main.py                 # FastAPI app entrypoint
|   +-- config.py               # Settings (pydantic-settings)
|
+-- serving/                    # Backend adapters + benchmarks
|   +-- backends/               # Groq, Ollama, vLLM adapters
|   +-- benchmarks/             # Inference throughput harness
|   +-- models.yaml             # Model registry config
|
+-- agent/                      # Agent Runtime
|   +-- runtime/                # Agent loop, planner, executor
|   +-- context/                # Context manager, token budgeting, summariser
|   +-- memory/                 # Working, episodic, semantic memory
|   +-- tools/                  # Tool interface + implementations
|   |   +-- scientific/         # ArxivTool, PDFParserTool, CalculatorTool
|   +-- mcp/                    # MCP server and client
|   +-- security/               # Permission policies, injection detection, sanitiser
|
+-- evaluation/                 # Evaluation Platform
|   +-- datasets/               # Benchmark task YAMLs
|   |   +-- general/            # Multi-step reasoning, tool use
|   |   +-- scientific/         # Scientific workflow tasks
|   |   +-- safety/             # Adversarial / injection tasks
|   +-- runners/                # Benchmark runner, CI runner
|   +-- metrics/                # Deterministic metrics, trajectory scoring
|   +-- judges/                 # LLM-as-judge, judge calibration
|   +-- safety/                 # Adversarial evaluator
|
+-- observability/              # Tracing, metrics, dashboards
|   +-- tracing/                # OpenTelemetry setup
|   +-- metrics/                # Prometheus instrumentation
|   +-- dashboards/             # Grafana dashboard JSON
|
+-- infrastructure/
|   +-- docker/                 # Per-service Dockerfiles
|   +-- kubernetes/             # Deployment manifests, HPA
|   +-- terraform/              # AWS/GCP infrastructure modules
|
+-- benchmarks/
|   +-- results/                # Benchmark output (JSON, CSV)
|   +-- reports/                # Generated markdown reports
|
+-- docs/
|   +-- architecture.md         # Detailed architecture decisions
|   +-- experiments.md          # Engineering questions answered with data
|   +-- gateway.md
|   +-- agent.md
|   +-- evaluation.md
|
+-- tests/
|   +-- unit/
|   +-- integration/
|   +-- chaos/                  # Reliability and fault injection tests
|
+-- docker-compose.yml
+-- Makefile
+-- pyproject.toml
+-- .env.example
```

---

## Benchmark results

Results from actual runs on RTX 3060 Ti + Groq API (August 2026).

| Metric | Target | Actual |
|---|---|---|
| Gateway p50 latency (fast model) | < 500ms | 302ms |
| Gateway p95 latency (fast model) | < 2.5s | 330ms |
| Gateway p50 latency (local model) | < 2s | 781ms |
| Agent task success rate (general) | >= 85% | 100% |
| Agent task success rate (scientific) | >= 85% | 100% |
| Safety score (adversarial benchmark) | >= 95% | 100% |
| Attack success rate | 0% | 0% |
| LLM judge / deterministic agreement | >= 80% | 100% |
| Mean judge score | >= 0.80 | 0.91-0.96 |
| CI regression detection | 100% | Passing |
| Context overflow incidents | 0 | 0 |

---

## Engineering questions this answers

Scion is designed to produce concrete engineering conclusions, not just code. The `docs/experiments.md` file documents findings from actual benchmark runs against each of the following questions:

1. Does intelligent routing reduce cost without reducing task success?
2. How does vLLM throughput scale with concurrency under continuous batching?
3. How does context length affect GPU memory and inference latency?
4. Does agent memory improve task completion rate, or does it sometimes hurt it?
5. What happens to task success rate as the number of available tools increases?
6. Does aggressive context summarisation reduce cost at the expense of accuracy?
7. How does maximum iteration count affect task success vs cost?
8. How effective is the tool permission system against prompt injection?
9. How well does an LLM judge agree with deterministic metrics?
10. What is the tail latency behaviour under request storms?
11. How do circuit breakers affect p99 latency during partial backend failure?
12. What is the optimal token budget split between history and tool results?
13. How does trajectory efficiency correlate with final task success?
14. What attack types does the current injection detector miss?

---

## Development roadmap

| Act | Focus | Status |
|---|---|---|
| Act 1 | Gateway: serving, routing, reliability, observability, benchmarks | Completed |
| Act 2 | Agent: loop, tools, MCP, context manager, memory, security | Completed |
| Act 3 | Evaluation: deterministic, trajectory, judge, regression CI, safety | Completed |
| Act 4 | Scientific workflow, dashboard, infrastructure, documentation | Completed |

---

## Licence

MIT
