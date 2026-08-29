from __future__ import annotations

import itertools

from gateway.routing.router import RouterStrategy, RoutingContext, RoutingDecision


class RoundRobinStrategy(RouterStrategy):
    """Cycles through healthy models in declaration order."""

    def __init__(self) -> None:
        self._counter = itertools.count()

    @property
    def name(self) -> str:
        return "round_robin"

    async def route(self, ctx: RoutingContext) -> RoutingDecision:
        models = ctx.available_models
        if not models:
            raise RuntimeError("No models available for routing")

        idx = next(self._counter) % len(models)
        selected = models[idx]
        fallback = models[idx + 1 :] + models[:idx]

        return RoutingDecision(
            model=selected,
            strategy_used=self.name,
            reason=f"Round robin index {idx}",
            fallback_chain=fallback,
        )
