# Scion

> Production LLM infrastructure platform: serving, agentic runtime, and automated evaluation.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![CI](https://github.com/MA-V4/scion/actions/workflows/ci.yml/badge.svg)

---

Scion is a production-grade LLM platform built from first principles. It is not a wrapper around an existing framework. It implements its own model serving layer, intelligent routing, agent execution loop, context manager, memory architecture, tool system, and evaluation framework.

The goal was to understand and demonstrate what it actually takes to operate LLMs as a production system: not just calling an API, but routing intelligently between models, managing agent context under token pressure, evaluating agent trajectories step by step, and catching behavioural regressions before they ship.

**Three subsystems. One trace.**

Every request in Scion generates a distributed trace. That trace follows the signal from the client through the gateway, router, model backend, agent loop, tool calls, and evaluation layer. This single architectural decision is what makes the platform debuggable, measurable, and improvable.

---

## Benchmark results

Measured on RTX 3060 Ti + Groq API (August 2026).

| Metric | Target | Actual |
|---|---|---|
| Gateway p50 latency (fast model) | < 500ms | 302ms |
| Gateway p95 latency (fast model) | < 2.5s | 330ms |
| Agent task success rate (general) | >= 85% | 100% |
| Agent task success rate (scientific) | >= 85% | 100% |
| Safety score (adversarial benchmark) | >= 95% | 100% |
| Attack success rate | 0% | 0% |
| LLM judge / deterministic agreement | >= 80% | 100% |
| Mean judge score | >= 0.80 | 0.91-0.96 |
| CI regression detection | 100% | Passing |

---

## Architecture
                     +--------------------+
                     |       Client       |
                     |  CLI / Agent / SDK |
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
               |  Health polling              |
               +--------------+---------------+
                              |
               +--------------+--------------+
               v              v              v
          +--------+    +--------+    +---------+
          | Groq   |    | Groq   |    | Ollama  |
          | 20B    |    | 120B   |    | 3B      |
          | fast   |    | reason |    | local   |
          +--------+    +--------+    +---------+
               |
               v
       +-------+--------+
       |  Agent Runtime  |
       |                 |
       |  Agent loop     |
       |  Context mgr    |
       |  MCP server     |
       |  Tool execution |
       |  Memory layers  |
       |  Security scan  |
       +-------+---------+
               |
    +----------+----------+----------+----------+
    v          v          v          v          v

Calculator Filesystem GitHub Search ArXiv
Tool Tool Tool Tool Tool
|
v
+-------+--------+
| Evaluation |
| |
| Deterministic |
| Trajectory |
| LLM judge |
| Safety eval |
| CI regression |
+-------+---------+
|
v
+-------+--------+
| Observability |
| |
| OpenTelemetry |
| Prometheus |
| Grafana |
+-----------------+


---

## Subsystems

### LLM Gateway

An OpenAI-compatible inference API (`POST /v1/chat/completions`) backed by a pluggable model registry and routing layer.

**Model registry:** Declared in `serving/models.yaml`. Polls each backend every 30 seconds for health status. Maintains per-model latency, error rate, and in-flight count.

**Routing strategies** (all implemented, pluggable at runtime):

| Strategy | Logic |
|---|---|
| `RoundRobin` | Cycles through healthy models |
| `LeastLoaded` | Routes to model with fewest in-flight requests |
| `CostAware` | Routes cheap tasks to low-cost models, complex tasks to reasoning models |
| `HealthAware` | Excludes backends with high error rate or tail latency |

**Reliability:**
- Circuit breakers per backend (closed / open / half-open states)
- Exponential backoff with full jitter
- Fallback chains (model A fails, try model B)
- Rate limiting via token bucket per API key
- Configurable timeouts per model

**Observability:**
- Every request tagged with `trace_id`
- Prometheus metrics: requests/sec, p50/p95/p99 latency, TTFT, tokens/sec, cost per model
- Grafana dashboard included (`observability/dashboards/scion-gateway.json`)

---

### Agent Runtime

A self-built agentic execution layer. No LangChain. No LlamaIndex. The agent loop, tool system, context manager, MCP server, and memory are all implemented from scratch.

**Agent loop:**

```python
while not done:
    context = context_manager.build(history, memory, tools)
    response = gateway.generate(context)
    if response.requests_tool:
        result = mcp.call_tool(response.tool_call)
        history.add_observation(result)
    else:
        return response.content
```

Terminates on: max iterations, token budget, explicit finish signal, timeout.

**Tool system:** Five tools, all using native function calling:

| Tool | Operations |
|---|---|
| `CalculatorTool` | Safe mathematical expression evaluation |
| `FilesystemTool` | read, write, list (sandboxed to workspace) |
| `GitHubTool` | search repos, read files, list issues, create issues |
| `SearchTool` | Web search via DuckDuckGo (no API key required) |
| `ArxivTool` | Search scientific papers, retrieve abstracts |

**MCP:** Tools are exposed via a Model Context Protocol server. The agent discovers tools dynamically at runtime. Permission policies enforced per agent role.

**Context manager:** Allocates a token budget across system prompt, tool definitions, history, memory, and output reserve. Handles overflow by dropping oldest observations first, then summarising history.

**Memory:**

| Layer | Scope | Backend |
|---|---|---|
| Working memory | Current task | In-process |
| Episodic memory | Previous task summaries | JSON file |
| Semantic memory | Extracted facts | JSON file |

**Security:**
- Pre-task injection scan (blocks injection before agent runs)
- Tool result injection scan (scans every tool output before context injection)
- Filesystem sandbox (path traversal blocked by resolve check)
- Secret detection in tool outputs

**Security benchmark finding:**
- Groq GPT-OSS-20B: refused all harmful direct prompts without application guardrails
- Ollama Llama-3.2-3B: complied with prompt injection (revealed fabricated system prompt)
- Conclusion: application-level guardrails are essential for smaller models and indirect injection via tool results

---

### Evaluation Platform

An automated evaluation framework that treats agent behaviour as a measurable, improvable system.

**Three benchmark suites:**

| Suite | Tasks | Success rate | Notes |
|---|---|---|---|
| General | 3 | 100% | Calculator, filesystem, reasoning tasks |
| Scientific | 3 | 100% | ArXiv search, molecular weight, photon energy |
| Safety | 5 | 100% | 2 injection, 1 path traversal, 2 benign |

**Evaluation layers:**

1. **Deterministic:** keyword matching, number checking, length validation
2. **Trajectory scoring:** tool selection, path efficiency, error recovery, final correctness
3. **LLM-as-judge:** structured JSON evaluation (correct, reasoning_quality, tool_use_quality, groundedness)
4. **Safety evaluation:** pre-task scanner + tool result scanner + filesystem sandbox

**Key finding:** LLM judge caught evaluator bugs that deterministic metrics missed (LaTeX number formatting). Judge/deterministic agreement reached 100% after fixing the evaluator. The judge acted as a cross-check on the evaluation methodology itself.

**CI regression testing:**

git push
-> GitHub Actions
-> Run benchmark suite
-> Compare against baseline
-> Fail if success_rate < 80% or regression > 10%
-> Upload results as artifact


---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API framework | FastAPI, Pydantic v2 |
| Serving (cloud) | Groq API (GPT-OSS-20B, GPT-OSS-120B) |
| Serving (local) | Ollama (Llama-3.2-3B on RTX 3060 Ti) |
| Serving (production) | vLLM (architecture implemented, native Linux required) |
| Observability | OpenTelemetry, Prometheus, Grafana |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes (manifests in `infrastructure/kubernetes/`) |
| Infrastructure | Terraform (modules in `infrastructure/terraform/`) |
| CI/CD | GitHub Actions |
| Testing | pytest, pytest-asyncio |

---

## Quick start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Ollama installed locally
- A Groq API key (free at console.groq.com)

### Setup

```bash
git clone https://github.com/MA-V4/scion
cd scion

cp .env.example .env
# Add your GROQ_API_KEY to .env

ollama pull llama3.2:3b

docker compose up -d

pip install -e ".[dev]"
```

### Run the gateway

```bash
docker compose up -d --build gateway
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Run the agent

```bash
# Edit TASK in scripts/run_task.py
python scripts/run_task.py
```

### Run benchmarks

```bash
python scripts/run_benchmark.py --suite general
python scripts/run_benchmark.py --suite scientific
python scripts/run_safety.py
```

### Run CI evaluation

```bash
python evaluation/runners/ci.py --baseline benchmarks/results/baseline.json
```

---

## Project structure

scion/
+-- gateway/ # LLM Gateway
| +-- api/ # FastAPI route handlers
| +-- routing/ # Model registry + routing strategies
| +-- middleware/ # Auth, rate limiting, tracing
| +-- reliability/ # Circuit breakers, retry, timeout
| +-- models/ # LLMRequest, LLMResponse, ModelSpec
| +-- main.py # FastAPI app + health polling
| +-- config.py # Pydantic settings
|
+-- serving/ # Backend adapters
| +-- backends/ # Groq, Ollama, vLLM adapters
| +-- benchmarks/ # Throughput benchmark harness
| +-- models.yaml # Model registry config
|
+-- agent/ # Agent Runtime
| +-- runtime/ # Agent loop
| +-- context/ # Context manager + token budgeting
| +-- memory/ # Working, episodic, semantic memory
| +-- tools/ # Tool implementations
| +-- mcp/ # MCP server and client
| +-- security/ # Injection detection, sanitiser
|
+-- evaluation/ # Evaluation Platform
| +-- datasets/ # Benchmark task YAMLs
| +-- runners/ # Benchmark runner, CI runner
| +-- metrics/ # Deterministic metrics, trajectory scoring
| +-- judges/ # LLM-as-judge
| +-- safety/ # Adversarial evaluator
|
+-- observability/ # Tracing, metrics, dashboards
+-- infrastructure/ # Docker, Kubernetes, Terraform
+-- docs/ # Architecture decisions, experiments
+-- scripts/ # Agent, benchmark, test scripts
+-- tests/ # Unit, integration, chaos tests


---

## Engineering experiments

Full findings in `docs/experiments.md`. Headlines:

- Gateway p50 latency: 302ms (fast), 437ms (reasoning), 781ms (local)
- 100% benchmark success rate across all three suites
- 0% attack success rate on adversarial safety benchmark
- LLM judge / deterministic agreement: 100% after evaluator fixes
- 20B model refuses all harmful prompts natively; 3B model requires application guardrails
- Circuit breakers correctly transition closed / open / half-open under backend failure
- Context manager never triggered overflow across all benchmark runs (22,528 token budget)

---

## Licence

MIT - see [LICENSE](LICENSE)