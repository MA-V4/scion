from __future__ import annotations


class SemanticMemory:
    """
    Postgres-backed fact store.
    Facts are extracted from previous tasks and retrieved by relevance.
    Example entries: 'user_prefers_python', 'project_database: postgresql'
    """

    async def store_fact(self, fact: str, value: str, confidence: float = 1.0) -> None:
        # TODO: UPSERT into semantic_memory table
        raise NotImplementedError

    async def retrieve(self, context: str, limit: int = 10) -> list[str]:
        # TODO: SELECT facts ordered by relevance to the context string
        # Initial implementation: simple keyword overlap; later: embedding similarity
        raise NotImplementedError

    async def extract_facts_from_trace(self, task: str, final_answer: str) -> list[str]:
        # TODO: call gateway to extract durable facts from the completed task
        raise NotImplementedError
