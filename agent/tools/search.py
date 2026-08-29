from __future__ import annotations

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class SearchInput(BaseModel):
    query: str
    max_results: int = 5


class SearchTool(Tool):
    """Web search via Brave Search API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web for current information."

    @property
    def input_schema(self) -> type[BaseModel]:
        return SearchInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.NETWORK}

    async def execute(self, input: BaseModel) -> ToolResult:
        # TODO: POST to Brave Search API, return structured results
        raise NotImplementedError
