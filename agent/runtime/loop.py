from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from agent.models.agent import AgentConfig, AgentStep, AgentTrace


@dataclass
class AgentLoop:
    """
    Core agent execution loop. No framework dependencies.

    Cycle:
      build_context -> generate -> check_tool_call -> execute_tool -> add_observation -> repeat
    Terminates on: max_iterations, token_budget_exceeded, explicit finish, timeout.
    """

    config: AgentConfig

    async def run(self, task: str) -> AgentTrace:
        trace = AgentTrace(task=task, started_at=time.time())
        history: list[dict[str, Any]] = []

        for iteration in range(self.config.max_iterations):
            step = await self._step(task, history, iteration, trace)
            trace.steps.append(step)
            history.append({"role": "assistant", "content": step.response})

            if step.is_terminal:
                break

            if step.tool_call:
                result = await self._execute_tool(step.tool_call)
                history.append(
                    {
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": step.tool_call.get("id", ""),
                    }
                )
                trace.tool_calls_made += 1

            if trace.total_tokens >= self.config.token_budget:
                trace.termination_reason = "token_budget_exceeded"
                break
        else:
            trace.termination_reason = "max_iterations"

        trace.finished_at = time.time()
        return trace

    async def _step(self, task: str, history: list, iteration: int, trace: AgentTrace) -> AgentStep:
        # TODO:
        # 1. context_manager.build(task, history, memory, tools) -> context
        # 2. gateway.generate(context) -> response
        # 3. Parse response for tool_call or finish signal
        # 4. Record token counts into trace
        raise NotImplementedError

    async def _execute_tool(self, tool_call: dict[str, Any]) -> Any:
        # TODO:
        # 1. Look up tool in registry
        # 2. Validate permissions
        # 3. Deserialise input against tool.input_schema
        # 4. Call tool.execute(input)
        # 5. Return ToolResult
        raise NotImplementedError
