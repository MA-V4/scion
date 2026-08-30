import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.filesystem import FilesystemTool
from agent.tools.scientific.calculator import CalculatorTool
from agent.tools.scientific.arxiv import ArxivTool
from agent.tools.search import SearchTool
from agent.tools.github import GitHubTool


TASK = """
Search for recent developments in mixture-of-experts LLM architectures,
find 2 relevant arXiv papers on the topic, get the GitHub repo info for
mistralai/mistral-src, calculate how many parameters a 8x7B MoE model has
if each expert has 7 billion parameters and only 2 are active per token,
then write a structured research summary to moe_research.txt covering
what you found.
"""

async def main():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(FilesystemTool())
    registry.register(ArxivTool())
    registry.register(SearchTool())
    registry.register(GitHubTool())

    config = AgentConfig(
        model="fast",
        max_iterations=10,
        token_budget=16384,
        timeout_s=120.0,
        allowed_tools=["calculator", "filesystem", "arxiv", "search", "github"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print(f"Running task: {TASK[:80].strip()}...")
    trace = await agent.run(TASK.strip())

    print(f"\\nTermination: {trace.termination_reason}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.tool_calls_made}")
    print(f"Tokens: {trace.total_tokens}")
    print(f"Duration: {round(trace.finished_at - trace.started_at, 2)}s")
    print(f"\\nFinal answer:\\n{trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
