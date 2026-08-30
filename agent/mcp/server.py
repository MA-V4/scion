from __future__ import annotations

from typing import Any

import structlog

from agent.tools.base import ToolRegistry, ToolResult

log = structlog.get_logger()


class MCPServer:
    """
    Model Context Protocol server.
    Exposes the tool registry to agents for dynamic tool discovery.
    Enforces permission policies before tool execution.
    """

    def __init__(self, registry: ToolRegistry, allowed_tools: set[str] | None = None) -> None:
        self._registry = registry
        self._allowed = allowed_tools

    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool schemas for all allowed tools."""
        schemas = self._registry.list_schemas(allowed=self._allowed)
        log.info("mcp.list_tools", count=len(schemas))
        return schemas

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool by name with the given arguments."""
        if self._allowed and tool_name not in self._allowed:
            raise PermissionError(f"Tool '{tool_name}' is not in the allowed set")

        try:
            tool = self._registry.get(tool_name)
        except KeyError:
            raise KeyError(f"Tool '{tool_name}' not registered") from None

        input_model = tool.input_schema(**arguments)
        result: ToolResult = await tool.execute(input_model)

        log.info(
            "mcp.tool_executed",
            tool=tool_name,
            success=result.success,
            execution_time_ms=round(result.execution_time_ms, 1),
        )

        if not result.success:
            raise RuntimeError(f"Tool '{tool_name}' failed: {result.error}")

        return result.output


class MCPClient:
    """
    Client interface for the MCP server.
    The agent uses this to discover and call tools without knowing their implementations.
    """

    def __init__(self, server: MCPServer) -> None:
        self._server = server

    def list_tools(self) -> list[dict[str, Any]]:
        return self._server.list_tools()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return await self._server.call_tool(tool_name, arguments)