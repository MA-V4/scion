from __future__ import annotations

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class ArxivSearchInput(BaseModel):
    query: str
    max_results: int = 5
    sort_by: str = "relevance"


class ArxivTool(Tool):
    """Search arXiv for scientific papers. Uses the public arXiv API (no auth required)."""

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def description(self) -> str:
        return (
            "Search arXiv for scientific papers. Returns titles, authors, abstracts, "
            "and PDF links. Use for retrieving literature on a scientific topic."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return ArxivSearchInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.NETWORK}

    async def execute(self, input: BaseModel) -> ToolResult:
        # TODO: query http://export.arxiv.org/api/query, parse Atom XML response
        raise NotImplementedError
