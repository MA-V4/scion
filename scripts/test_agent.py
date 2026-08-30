import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.scientific.arxiv import ArxivTool


async def main():
    registry = ToolRegistry()
    registry.register(ArxivTool())

    config = AgentConfig(
        model="fast",
        max_iterations=5,
        token_budget=8192,
        timeout_s=60.0,
        allowed_tools=["arxiv"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print("Testing ArxivTool...")
    trace = await agent.run(
        "Find 3 recent papers on transformer attention mechanisms and summarise their key contributions."
    )

    print(f"Termination reason: {trace.termination_reason}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.tool_calls_made}")
    print(f"Final answer: {trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
