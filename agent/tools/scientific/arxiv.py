from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class ArxivSearchInput(BaseModel):
    query: str
    max_results: int = 5


@dataclass
class ArxivPaper:
    id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    pdf_url: str


NS = "http://www.w3.org/2005/Atom"


class ArxivTool(Tool):
    """Search arXiv for scientific papers. Uses the public API, no auth required."""

    BASE_URL = "http://export.arxiv.org/api/query"

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def description(self) -> str:
        return (
            "Search arXiv for scientific papers. "
            "Returns titles, authors, abstracts, and PDF links. "
            "Use for retrieving literature on a scientific topic."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return ArxivSearchInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.NETWORK}

    async def execute(self, input: BaseModel) -> ToolResult:
        assert isinstance(input, ArxivSearchInput)
        start = time.time()

        try:
            params = urllib.parse.urlencode(
                {
                    "search_query": f"all:{input.query}",
                    "start": 0,
                    "max_results": min(input.max_results, 10),
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                }
            )
            url = f"{self.BASE_URL}?{params}"

            with urllib.request.urlopen(url, timeout=15) as resp:
                xml_data = resp.read().decode("utf-8")

            papers = self._parse(xml_data)

            return ToolResult(
                success=True,
                output=[
                    {
                        "id": p.id,
                        "title": p.title,
                        "authors": p.authors[:3],
                        "abstract": p.abstract[:500] + "..."
                        if len(p.abstract) > 500
                        else p.abstract,
                        "published": p.published,
                        "pdf_url": p.pdf_url,
                    }
                    for p in papers
                ],
                execution_time_ms=(time.time() - start) * 1000,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
            )

    def _parse(self, xml_data: str) -> list[ArxivPaper]:
        root = ET.fromstring(xml_data)
        papers = []

        for entry in root.findall(f"{{{NS}}}entry"):
            raw_id = entry.findtext(f"{{{NS}}}id", "")
            arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

            title_el = entry.find(f"{{{NS}}}title")
            title = (
                title_el.text.strip().replace("\n", " ")
                if title_el is not None and title_el.text
                else ""
            )

            abstract_el = entry.find(f"{{{NS}}}summary")
            abstract = (
                abstract_el.text.strip().replace("\n", " ")
                if abstract_el is not None and abstract_el.text
                else ""
            )

            published_el = entry.find(f"{{{NS}}}published")
            published = (
                published_el.text[:10] if published_el is not None and published_el.text else ""
            )

            authors = [a.findtext(f"{{{NS}}}name", "") for a in entry.findall(f"{{{NS}}}author")]

            pdf_url = ""
            for link in entry.findall(f"{{{NS}}}link"):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href", "")
                    break

            papers.append(
                ArxivPaper(
                    id=arxiv_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    published=published,
                    pdf_url=pdf_url,
                )
            )

        return papers
