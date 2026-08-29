# Engineering Experiments

This document records findings from actual benchmark runs.
Numbers are filled in as each experiment is completed.

## 1. Does intelligent routing reduce cost without reducing task success?

Hypothesis: CostAwareStrategy can route simple tasks to the fast model and save cost
without measurably reducing task success rate.

Setup: 100 tasks split 50/50 simple/complex. Compare RoundRobin vs CostAware.
Results: (pending)

## 2. How does vLLM throughput scale with concurrency under continuous batching?

Setup: benchmark harness at concurrency 1, 2, 4, 8, 16, 32 with short/medium/long prompts.
Results: (pending)

## 3. How does context length affect GPU memory?

Setup: vary input token count from 512 to 32k, record GPU memory via nvidia-smi.
Results: (pending)

## 4. Does agent memory improve task completion rate?

Hypothesis: semantic memory improves success on tasks that rely on facts from prior runs.
Benchmark: 30 tasks, agent with vs without memory. Tasks designed to benefit from prior knowledge.
Results: (pending)

## 5. What happens to task success as tool count increases?

Hypothesis: more tools increases decision complexity and may hurt performance past a threshold.
Setup: 0, 2, 4, 8, 12 tools available. Fixed task set.
Results: (pending)

## 6. Does aggressive context summarisation reduce accuracy?

Setup: compare full-history context vs summarised context on long tasks (>10 steps).
Results: (pending)

## 7. How does max_iterations affect success vs cost?

Setup: vary max_iterations from 5 to 30. Plot success rate and total token cost.
Results: (pending)

## 8. How effective is the tool permission system against prompt injection?

Setup: 50 adversarial tasks. Permission system on vs off.
Results: (pending)

## 9. LLM judge vs deterministic metric agreement

Setup: 30 tasks with hand-labelled ground truth. Compare judge scores vs binary task_success.
Results: (pending)

## 10. Tail latency under request storms

Setup: 200 concurrent requests. Record p99 latency. Circuit breakers on vs off.
Results: (pending)
