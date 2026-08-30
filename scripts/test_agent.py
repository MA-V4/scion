import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.search import SearchTool


async def main():
    registry = ToolRegistry()
    registry.register(SearchTool())

    config = AgentConfig(
        model="fast",
        max_iterations=5,
        token_budget=8192,
        timeout_s=60.0,
        allowed_tools=["search"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print("Testing SearchTool...")
    trace = await agent.run(
        "Search for what vLLM is and summarise what you find."
    )

    print(f"Termination reason: {trace.termination_reason}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.tool_calls_made}")
    print(f"Final answer: {trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
