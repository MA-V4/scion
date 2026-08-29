from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from gateway.models.request import LLMRequest, LLMResponse, StreamChunk


class Backend(ABC):
    """Abstract interface for all model backends."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Run a non-streaming inference call and return the full response."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Run a streaming inference call and yield chunks as they arrive."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backend is reachable and healthy."""
        raise NotImplementedError
