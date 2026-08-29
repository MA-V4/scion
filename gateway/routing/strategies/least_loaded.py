from __future__ import annotations

from gateway.routing.router import RoutingContext, RoutingDecision, RouterStrategy


class LeastLoadedStrategy(RouterStrategy):
    """Routes to the model with the fewest in-flight requests."""

    @property
    def name(self) -> str:
        return "least_loaded"

    async def route(self, ctx: RoutingContext) -> RoutingDecision:
        # TODO: in production, read in-flight counters from Redis
        sorted_models = sorted(ctx.available_models, key=lambda m: m.health.in_flight)
        selected = sorted_models[0]

        return RoutingDecision(
            model=selected,
            strategy_used=self.name,
            reason=f"Fewest in-flight ({selected.health.in_flight})",
            fallback_chain=sorted_models[1:],
        )
