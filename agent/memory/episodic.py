from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Episode:
    task: str
    summary: str
    outcome: str
    tool_calls_made: int
    tokens_used: int
    steps_taken: int
    created_at: float


class EpisodicMemory:
    """
    File-backed store of previous task summaries.
    Uses JSON for simplicity - no Postgres dependency during development.
    Retrieved for new tasks to provide historical context.
    """

    def __init__(self, storage_path: str = "/tmp/scion-memory/episodes.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._episodes: list[Episode] = self._load()

    def _load(self) -> list[Episode]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text())
            return [Episode(**e) for e in data]
        except Exception:
            return []

    def _save(self) -> None:
        self._path.write_text(json.dumps([asdict(e) for e in self._episodes], indent=2))

    def store(self, episode: Episode) -> None:
        self._episodes.append(episode)
        self._save()

    def retrieve(self, task: str, limit: int = 3) -> list[Episode]:
        """Return the most recent episodes, most recent first."""
        return list(reversed(self._episodes[-limit:]))

    def summarise_for_context(self, task: str, limit: int = 3) -> list[str]:
        """Return episode summaries formatted for injection into context."""
        episodes = self.retrieve(task, limit)
        if not episodes:
            return []
        return [
            f"Previous task: {e.task[:100]} -> {e.outcome} ({e.steps_taken} steps, {e.tokens_used} tokens)"
            for e in episodes
        ]

    def clear(self) -> None:
        self._episodes = []
        self._save()