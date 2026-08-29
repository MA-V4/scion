from __future__ import annotations

from agent.tools.base import ToolRegistry


class MCPServer:
    """
    Model Context Protocol server.
    Exposes the tool registry to agents for dynamic tool discovery.
    Enforces permission policies before tool execution.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def list_tools(self, agent_role: str | None = None) -> list[dict]:
        # TODO: filter tools by agent_role permissions
        return self._registry.list_schemas()

    async def call_tool(
        self, tool_name: str, input_data: dict, agent_role: str | None = None
    ) -> dict:
        # TODO:
        # 1. Check agent_role has permission for tool_name
        # 2. Deserialise input_data via tool.input_schema
        # 3. Call tool.execute(input)
        # 4. Return serialised ToolResult
        raise NotImplementedError
