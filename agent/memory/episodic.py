from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Episode:
    task: str
    summary: str
    outcome: str
    tool_calls_made: int
    tokens_used: int
    created_at: datetime


class EpisodicMemory:
    """
    Postgres-backed store of previous task summaries.
    Retrieved for new tasks to provide historical context.
    """

    async def store(self, episode: Episode) -> None:
        # TODO: INSERT into episodes table
        raise NotImplementedError

    async def retrieve(self, task: str, limit: int = 5) -> list[Episode]:
        # TODO: SELECT recent episodes relevant to the task (simple recency or similarity)
        raise NotImplementedError
