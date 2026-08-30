from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
import structlog

from agent.context.manager import ContextBudget, ContextManager
from agent.mcp.server import MCPClient, MCPServer
from agent.memory.episodic import Episode, EpisodicMemory
from agent.memory.semantic import SemanticMemory
from agent.memory.working import WorkingMemory
from agent.models.agent import AgentConfig, AgentStep, AgentTrace
from agent.security.injection_detector import scan
from agent.tools.base import ToolRegistry

log = structlog.get_logger()

GUARDRAILS_ENABLED = True  # Set to True to re-enable


class AgentLoop:
    """
    Core agent execution loop. No framework dependencies.
    Uses native function calling via the gateway.
    """

    def __init__(self, config: AgentConfig, tool_registry: ToolRegistry | None = None) -> None:
        self._config = config
        self._registry = tool_registry or ToolRegistry()
        self._mcp = MCPClient(
            MCPServer(
                registry=self._registry,
                allowed_tools=set(config.allowed_tools) if config.allowed_tools else None,
            )
        )
        self._client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=60.0)
        self._context_manager = ContextManager(
            ContextBudget(
                system_prompt=2048,
                tool_definitions=4096,
                recent_history=8192,
                relevant_memory=2048,
                tool_results=4096,
                output_reserve=2048,
            )
        )
        self._working = WorkingMemory()
        self._episodic = EpisodicMemory()
        self._semantic = SemanticMemory()

    async def run(self, task: str) -> AgentTrace:
        trace = AgentTrace(task=task, started_at=time.time())
        history: list[dict[str, Any]] = [{"role": "user", "content": task}]
        self._working.clear()

        episodic_context = self._episodic.summarise_for_context(task)
        semantic_context = self._semantic.retrieve(task)
        memory_entries = episodic_context + semantic_context

        if memory_entries:
            log.info(
                "agent.memory.loaded",
                episodic=len(episodic_context),
                semantic=len(semantic_context),
            )

        log.info("agent.run.start", task=task[:80], max_iterations=self._config.max_iterations)

        try:
            async with asyncio.timeout(self._config.timeout_s):
                for iteration in range(self._config.max_iterations):
                    step = await self._step(history, iteration, memory_entries)
                    trace.steps.append(step)
                    trace.total_tokens += step.tokens_used

                    log.info(
                        "agent.step",
                        iteration=iteration,
                        tokens=step.tokens_used,
                        is_terminal=step.is_terminal,
                        has_tool_call=step.tool_call is not None,
                    )

                    if step.is_terminal:
                        trace.final_answer = step.response
                        trace.termination_reason = "finished"
                        break

                    if step.tool_call:
                        history.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [step.tool_call],
                            }
                        )
                        result = await self._execute_tool(step.tool_call)
                        history.append(
                            {
                                "role": "tool",
                                "tool_call_id": step.tool_call["id"],
                                "content": json.dumps(result),
                            }
                        )
                        trace.tool_calls_made += 1
                    else:
                        history.append({"role": "assistant", "content": step.response})

                    if trace.total_tokens >= self._config.token_budget:
                        trace.termination_reason = "token_budget_exceeded"
                        break
                else:
                    trace.termination_reason = "max_iterations"

        except TimeoutError:
            trace.termination_reason = "timeout"

        trace.finished_at = time.time()

        self._episodic.store(
            Episode(
                task=task,
                summary=trace.final_answer[:200] if trace.final_answer else "",
                outcome=trace.termination_reason,
                tool_calls_made=trace.tool_calls_made,
                tokens_used=trace.total_tokens,
                steps_taken=len(trace.steps),
                created_at=trace.started_at,
            )
        )

        log.info(
            "agent.run.complete",
            termination_reason=trace.termination_reason,
            steps=len(trace.steps),
            total_tokens=trace.total_tokens,
            tool_calls=trace.tool_calls_made,
            duration_s=round(trace.finished_at - trace.started_at, 2),
        )
        return trace

    async def _step(
        self, history: list[dict[str, Any]], iteration: int, memory_entries: list[str] | None = None
    ) -> AgentStep:
        tools = self._registry.list_schemas(
            allowed=set(self._config.allowed_tools) if self._config.allowed_tools else None
        )

        messages, usage = self._context_manager.build(
            system_prompt=self._config.system_prompt,
            history=history,
            tool_schemas=tools if tools else None,
            memory_entries=memory_entries if memory_entries else None,
        )

        if iteration == 0:
            log.info("context.usage", **usage)

        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "max_tokens": self._config.max_tokens_per_step,
            "temperature": 0.7,
        }

        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
            payload["tool_choice"] = "auto"

        start = time.time()
        resp = await self._client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

        latency_ms = (time.time() - start) * 1000
        choice = data["choices"][0]
        message = choice["message"]
        usage_data = data.get("usage", {})
        tokens_used = usage_data.get("total_tokens", 0)

        tool_calls = choice.get("tool_calls")
        if tool_calls:
            return AgentStep(
                iteration=iteration,
                response=message.get("content") or "",
                tool_call=tool_calls[0],
                is_terminal=False,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
            )

        return AgentStep(
            iteration=iteration,
            response=message.get("content", ""),
            tool_call=None,
            is_terminal=True,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    async def _execute_tool(self, tool_call: dict[str, Any]) -> Any:
        name = tool_call.get("function", {}).get("name", "unknown")
        raw_args = tool_call.get("function", {}).get("arguments", "{}")
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

        log.info("agent.tool_call", tool=name, args=args)

        try:
            result = await self._mcp.call_tool(name, args)

            if GUARDRAILS_ENABLED:
                result_text = str(result)
                scan_result = scan(result_text)
                if scan_result.is_injection:
                    log.warning(
                        "agent.security.injection_detected",
                        tool=name,
                        patterns=scan_result.injection_matches,
                    )
                    return f"[BLOCKED] Tool result from '{name}' was flagged for prompt injection and discarded."
                if scan_result.has_secrets:
                    log.warning(
                        "agent.security.secret_detected",
                        tool=name,
                        patterns=scan_result.secret_matches,
                    )
                    return f"[BLOCKED] Tool result from '{name}' contained potential secrets and was redacted."

            return result

        except PermissionError as e:
            return f"Permission denied: {e}"
        except KeyError as e:
            return f"Tool not found: {e}"
        except Exception as e:
            return f"Tool execution failed: {e}"

    async def close(self) -> None:
        await self._client.aclose()
