from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class SearchInput(BaseModel):
    query: str
    max_results: int = 5


class SearchTool(Tool):
    """Web search via DuckDuckGo. No API key required."""

    DDG_URL = "https://api.duckduckgo.com/"

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return (
            "Search the web for current information. "
            "Returns titles, URLs, and snippets from search results. "
            "Use for finding facts, news, or information not in your training data."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return SearchInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.NETWORK}

    async def execute(self, input: BaseModel) -> ToolResult:
        assert isinstance(input, SearchInput)
        start = time.time()

        try:
            params = urllib.parse.urlencode(
                {
                    "q": input.query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                }
            )
            url = f"{self.DDG_URL}?{params}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Scion/0.1 (research agent)"},
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = []

            if data.get("AbstractText"):
                results.append(
                    {
                        "title": data.get("Heading", ""),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data["AbstractText"],
                        "source": data.get("AbstractSource", ""),
                    }
                )

            for topic in data.get("RelatedTopics", []):
                if len(results) >= input.max_results:
                    break
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(
                        {
                            "title": topic.get("Text", "")[:80],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                            "source": "DuckDuckGo",
                        }
                    )

            if not results:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"No results found for '{input.query}'",
                    execution_time_ms=(time.time() - start) * 1000,
                )

            return ToolResult(
                success=True,
                output=results[: input.max_results],
                execution_time_ms=(time.time() - start) * 1000,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
            )
