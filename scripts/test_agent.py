import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.scientific.calculator import CalculatorTool


async def main():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    config = AgentConfig(
        model="fast",
        max_iterations=5,
        token_budget=8192,
        timeout_s=60.0,
        allowed_tools=["calculator"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print("Running agent with calculator tool...")
    trace = await agent.run(
        "Calculate 15% of 847. Use the calculator tool."
    )

    print(f"\nTermination reason: {trace.termination_reason}")
    print(f"Steps taken: {len(trace.steps)}")
    print(f"Total tokens: {trace.total_tokens}")
    print(f"Tool calls made: {trace.tool_calls_made}")
    print(f"Duration: {round(trace.finished_at - trace.started_at, 2)}s")
    print(f"\nFinal answer: {trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())