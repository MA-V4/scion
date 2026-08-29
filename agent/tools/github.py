from __future__ import annotations

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class SearchRepoInput(BaseModel):
    owner: str
    repo: str
    query: str


class CreateIssueInput(BaseModel):
    owner: str
    repo: str
    title: str
    body: str


class GitHubTool(Tool):
    """GitHub operations via the REST API. Requires a GITHUB_TOKEN."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "Search repositories, read files, list issues, and create issues on GitHub."

    @property
    def input_schema(self) -> type[BaseModel]:
        return SearchRepoInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.WRITE, ToolPermission.NETWORK}

    async def execute(self, input: BaseModel) -> ToolResult:
        # TODO: dispatch on operation, call GitHub REST API via httpx
        raise NotImplementedError
