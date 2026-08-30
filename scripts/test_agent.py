import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.github import GitHubTool


async def main():
    registry = ToolRegistry()
    registry.register(GitHubTool())

    config = AgentConfig(
        model="fast",
        max_iterations=5,
        token_budget=8192,
        timeout_s=60.0,
        allowed_tools=["github"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print("Testing GitHubTool...")
    trace = await agent.run(
        "Get the repository info for vllm-project/vllm and tell me its star count, language, and description."
    )

    print(f"Termination reason: {trace.termination_reason}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.tool_calls_made}")
    print(f"Final answer: {trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
