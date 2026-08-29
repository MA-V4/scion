from __future__ import annotations

from gateway.config import settings 
from gateway.models.registry import ModelProvider, ModelSpec
from serving.backends.base import Backend
from serving.backends.groq import GroqBackend
from serving.backends.ollama import OllamaBackend

class BackendFactory:
    """
    Maps a ModelSpec to the correct backend instance.
    All backend instances are cached after first creation.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Backend] = {}

    def get(self, spec: ModelSpec) -> Backend:
        if spec.name in self._cache:
            return self._cache[spec.name]

        backend = self._create(spec)
        self._cache[spec.name] = backend
        return backend

    def _create(self, spec: ModelSpec) -> Backend:
        if spec.provider == ModelProvider.GROQ:
            if not settings.groq_api_key:
                raise RuntimeError("GROQ_API_KEY is not set")
            return GroqBackend(spec=spec, api_key=settings.groq_api_key)

        if spec.provider == ModelProvider.OLLAMA:
            return OllamaBackend(spec=spec)

        raise ValueError(f"No backend implementation for provider '{spec.provider}'")

    async def close_all(self) -> None:
        for backend in self._cache.values():
            await backend.close()
        self._cache.clear()