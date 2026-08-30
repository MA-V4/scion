import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.filesystem import FilesystemTool
from agent.tools.scientific.calculator import CalculatorTool
from agent.tools.scientific.arxiv import ArxivTool
from agent.tools.search import SearchTool
from agent.tools.github import GitHubTool


async def main():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(FilesystemTool())
    registry.register(ArxivTool())
    registry.register(SearchTool())
    registry.register(GitHubTool())

    config = AgentConfig(
        model="fast",
        max_iterations=8,
        token_budget=16384,
        timeout_s=120.0,
        allowed_tools=["calculator", "filesystem", "arxiv", "search", "github"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print("Testing MCP with all tools...")
    trace = await agent.run(
        "Search for what the vLLM project is, then get the GitHub repo info for vllm-project/vllm "
        "and calculate how many stars it would have if it doubled. Write a summary to results.txt."
    )

    print(f"Termination reason: {trace.termination_reason}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.tool_calls_made}")
    print(f"Final answer: {trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
