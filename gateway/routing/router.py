from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from gateway.models.registry import ModelSpec
from gateway.models.request import LLMRequest
from gateway.routing.registry import ModelRegistry


@dataclass
class RoutingContext:
    request: LLMRequest
    available_models: list[ModelSpec]
    task_type: str | None = None
    latency_budget_ms: float | None = None
    cost_budget: float | None = None


@dataclass
class RoutingDecision:
    model: ModelSpec
    strategy_used: str
    reason: str
    fallback_chain: list[ModelSpec]


class RouterStrategy(ABC):
    """Abstract base for all routing strategies."""

    @abstractmethod
    async def route(self, ctx: RoutingContext) -> RoutingDecision:
        """Select a model given the routing context."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class ModelRouter:
    """
    Routes requests to model backends using a pluggable strategy.
    Falls back through a chain of models on failure.
    """

    def __init__(self, registry: ModelRegistry, strategy: RouterStrategy) -> None:
        self._registry = registry
        self._strategy = strategy

    async def route(self, request: LLMRequest) -> RoutingDecision:
        available = self._registry.list_healthy()
        if not available:
            raise RuntimeError("No healthy models available")

        ctx = RoutingContext(request=request, available_models=available)
        return await self._strategy.route(ctx)

    def set_strategy(self, strategy: RouterStrategy) -> None:
        self._strategy = strategy
