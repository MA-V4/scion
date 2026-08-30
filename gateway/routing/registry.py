from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import yaml

from gateway.models.registry import ModelHealth, ModelProvider, ModelSpec


class ModelRegistry:
    """
    Declarative model registry backed by models.yaml.
    Runtime health state is maintained in-process.
    Background polling updates health every POLL_INTERVAL seconds.
    """

    POLL_INTERVAL = 30.0

    def __init__(self) -> None:
        self._models: dict[str, ModelSpec] = {}
        self._poll_task: asyncio.Task | None = None

    def load_from_yaml(self, path: str | Path) -> None:
        with open(path) as f:
            config = yaml.safe_load(f)

        for entry in config.get("models", []):
            spec = ModelSpec(
                name=entry["name"],
                provider=ModelProvider(entry["provider"]),
                model_id=entry["model_id"],
                endpoint=entry.get("endpoint"),
                context_length=entry.get("context_length", 32768),
                cost_per_1m_input=entry.get("cost_per_1m_input", 0.0),
                cost_per_1m_output=entry.get("cost_per_1m_output", 0.0),
                capabilities=entry.get("capabilities", []),
            )
            self._models[spec.name] = spec

    def start_polling(self) -> None:
        """Start background health polling task."""
        self._poll_task = asyncio.create_task(self._poll_loop())

    def stop_polling(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()

    async def _poll_loop(self) -> None:
        import structlog
        log = structlog.get_logger()
        while True:
            await asyncio.sleep(self.POLL_INTERVAL)
            for name, spec in self._models.items():
                try:
                    healthy = await self._check_health(spec)
                    self._models[name].health.is_healthy = healthy
                    self._models[name].health.last_checked_at = time.time()
                    log.info("registry.health_poll", model=name, healthy=healthy)
                except Exception as e:
                    log.warning("registry.health_poll_failed", model=name, error=str(e))
                    self._models[name].health.is_healthy = False

    async def _check_health(self, spec: ModelSpec) -> bool:
        if spec.provider == ModelProvider.GROQ:
            async with httpx.AsyncClient(timeout=5.0) as client:
                from gateway.config import settings
                resp = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                )
                return resp.status_code == 200

        if spec.provider == ModelProvider.OLLAMA:
            endpoint = spec.endpoint or "http://localhost:11434"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{endpoint}/api/tags")
                return resp.status_code == 200

        if spec.provider == ModelProvider.VLLM:
            endpoint = spec.endpoint or "http://localhost:8080"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{endpoint}/health")
                return resp.status_code == 200

        return True

    def get(self, name: str) -> ModelSpec:
        if name not in self._models:
            raise KeyError(f"Model '{name}' not found in registry")
        return self._models[name]

    def list_healthy(self) -> list[ModelSpec]:
        return [m for m in self._models.values() if m.health.is_healthy]

    def all(self) -> list[ModelSpec]:
        return list(self._models.values())

    def update_health(self, model_name: str, health: ModelHealth) -> None:
        if model_name in self._models:
            health.last_checked_at = time.time()
            self._models[model_name].health = health