from __future__ import annotations

import json
from pathlib import Path


class SemanticMemory:
    """
    File-backed fact store.
    Facts are extracted from previous tasks and retrieved by keyword match.
    Example entries: 'user_prefers_python: true', 'project_database: postgresql'
    """

    def __init__(self, storage_path: str = "/tmp/scion-memory/semantic.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._facts: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._facts, indent=2))

    def store_fact(self, key: str, value: str) -> None:
        self._facts[key] = value
        self._save()

    def retrieve(self, context: str, limit: int = 10) -> list[str]:
        """Return facts whose keys appear in the context string."""
        context_lower = context.lower()
        matches = [
            f"{k}: {v}"
            for k, v in self._facts.items()
            if any(word in context_lower for word in k.lower().split("_"))
        ]
        return matches[:limit]

    def retrieve_all(self) -> list[str]:
        return [f"{k}: {v}" for k, v in self._facts.items()]

    def clear(self) -> None:
        self._facts = {}
        self._save()