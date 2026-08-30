from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class GitHubSearchInput(BaseModel):
    operation: str  # search_repos, list_issues, read_file, get_repo
    query: str | None = None
    owner: str | None = None
    repo: str | None = None
    path: str | None = None
    max_results: int = 5


class GitHubTool(Tool):
    """GitHub operations via the REST API. Read-only."""

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        self._token = os.environ.get("GITHUB_TOKEN", "")

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return (
            "Interact with GitHub repositories. "
            "Operations: "
            "'search_repos' (find repositories by query), "
            "'list_issues' (list open issues for owner/repo), "
            "'read_file' (read a file from owner/repo at path), "
            "'get_repo' (get repository metadata for owner/repo)."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return GitHubSearchInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.NETWORK}

    def _get(self, path: str) -> dict:
        url = f"{self.BASE_URL}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Scion/0.1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    async def execute(self, input: BaseModel) -> ToolResult:
        assert isinstance(input, GitHubSearchInput)
        start = time.time()

        try:
            if input.operation == "search_repos":
                if not input.query:
                    return ToolResult(
                        success=False, output=None, error="query required for search_repos"
                    )
                params = urllib.parse.urlencode({"q": input.query, "per_page": input.max_results})
                data = self._get(f"/search/repositories?{params}")
                results = [
                    {
                        "name": r["full_name"],
                        "description": r.get("description", ""),
                        "stars": r["stargazers_count"],
                        "url": r["html_url"],
                        "language": r.get("language", ""),
                    }
                    for r in data.get("items", [])
                ]
                return ToolResult(
                    success=True, output=results, execution_time_ms=(time.time() - start) * 1000
                )

            elif input.operation == "get_repo":
                if not input.owner or not input.repo:
                    return ToolResult(success=False, output=None, error="owner and repo required")
                data = self._get(f"/repos/{input.owner}/{input.repo}")
                return ToolResult(
                    success=True,
                    output={
                        "name": data["full_name"],
                        "description": data.get("description", ""),
                        "stars": data["stargazers_count"],
                        "forks": data["forks_count"],
                        "language": data.get("language", ""),
                        "topics": data.get("topics", []),
                        "url": data["html_url"],
                    },
                    execution_time_ms=(time.time() - start) * 1000,
                )

            elif input.operation == "list_issues":
                if not input.owner or not input.repo:
                    return ToolResult(success=False, output=None, error="owner and repo required")
                data = self._get(
                    f"/repos/{input.owner}/{input.repo}/issues?state=open&per_page={input.max_results}"
                )
                results = [
                    {
                        "number": i["number"],
                        "title": i["title"],
                        "state": i["state"],
                        "url": i["html_url"],
                        "created_at": i["created_at"][:10],
                    }
                    for i in data
                ]
                return ToolResult(
                    success=True, output=results, execution_time_ms=(time.time() - start) * 1000
                )

            elif input.operation == "read_file":
                if not input.owner or not input.repo or not input.path:
                    return ToolResult(
                        success=False, output=None, error="owner, repo, and path required"
                    )
                import base64

                data = self._get(f"/repos/{input.owner}/{input.repo}/contents/{input.path}")
                if data.get("encoding") == "base64":
                    content = base64.b64decode(data["content"]).decode("utf-8")
                else:
                    content = data.get("content", "")
                return ToolResult(
                    success=True,
                    output=content[:3000],
                    execution_time_ms=(time.time() - start) * 1000,
                )

            else:
                return ToolResult(
                    success=False, output=None, error=f"Unknown operation: {input.operation}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
            )
