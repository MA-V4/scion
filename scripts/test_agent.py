import asyncio
from agent.models.agent import AgentConfig
from agent.runtime.loop import AgentLoop
from agent.tools.base import ToolRegistry
from agent.tools.filesystem import FilesystemTool
from agent.tools.scientific.calculator import CalculatorTool


async def main():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(FilesystemTool())

    config = AgentConfig(
        model="fast",
        max_iterations=5,
        token_budget=8192,
        timeout_s=60.0,
        allowed_tools=["calculator", "filesystem"],
    )

    agent = AgentLoop(config=config, tool_registry=registry)

    print("Testing filesystem tool...")
    trace = await agent.run(
        "Write a file called hello.txt with the content Hello from Scion, "
        "then read it back and confirm the content."
    )

    print(f"Termination reason: {trace.termination_reason}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.tool_calls_made}")
    print(f"Final answer: {trace.final_answer}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
