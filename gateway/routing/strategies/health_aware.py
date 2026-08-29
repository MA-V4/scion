from __future__ import annotations

from gateway.routing.router import RouterStrategy, RoutingContext, RoutingDecision

ERROR_RATE_THRESHOLD = 0.10
LATENCY_P95_THRESHOLD_MS = 3000.0


class HealthAwareStrategy(RouterStrategy):
    """
    Excludes backends with high error rates or extreme tail latency.
    Falls back to lowest-error-rate backend.
    """

    @property
    def name(self) -> str:
        return "health_aware"

    async def route(self, ctx: RoutingContext) -> RoutingDecision:
        healthy = [
            m
            for m in ctx.available_models
            if m.health.error_rate < ERROR_RATE_THRESHOLD
            and m.health.latency_p95_ms < LATENCY_P95_THRESHOLD_MS
        ]

        if not healthy:
            healthy = sorted(ctx.available_models, key=lambda m: m.health.error_rate)

        selected = healthy[0]
        return RoutingDecision(
            model=selected,
            strategy_used=self.name,
            reason=f"Error rate {selected.health.error_rate:.2%}, p95 {selected.health.latency_p95_ms}ms",
            fallback_chain=healthy[1:],
        )
