from __future__ import annotations

from typing import Any


class WorkingMemory:
    """
    In-process memory for the current task only.
    Cleared between agent runs.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def clear(self) -> None:
        self._store.clear()

    def dump(self) -> dict[str, Any]:
        return dict(self._store)
