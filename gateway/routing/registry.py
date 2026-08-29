from __future__ import annotations

import time
from pathlib import Path

import yaml

from gateway.models.registry import ModelHealth, ModelProvider, ModelSpec


class ModelRegistry:
    """
    Declarative model registry backed by models.yaml.
    Runtime health state is maintained per-instance (in production, back this with Redis).
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelSpec] = {}

    def load_from_yaml(self, path: str | Path) -> None:
        """Load model specs from a YAML config file."""
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

    async def poll_health(self) -> None:
        """Poll all registered backends for health. Called on a background interval."""
        # TODO: implement per-provider health checks via the backend adapters
        raise NotImplementedError
