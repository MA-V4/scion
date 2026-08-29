from __future__ import annotations

from gateway.routing.router import RoutingContext, RoutingDecision, RouterStrategy


class CostAwareStrategy(RouterStrategy):
    """
    Routes cheap/short tasks to the lowest-cost model.
    Routes complex/long tasks to the best reasoning model.
    Falls back to lowest-cost model for unknown task types.
    """

    SIMPLE_TASK_TYPES = {"qa", "summarise", "classify", "extract"}
    REASONING_TASK_TYPES = {"reason", "code", "analyse", "plan"}

    @property
    def name(self) -> str:
        return "cost_aware"

    async def route(self, ctx: RoutingContext) -> RoutingDecision:
        task = ctx.task_type or self._classify_task(ctx.request.messages[-1].content)
        sorted_by_cost = sorted(
            ctx.available_models, key=lambda m: m.cost_per_1m_input
        )

        if task in self.REASONING_TASK_TYPES:
            # TODO: sort by capability score, not just cost
            selected = sorted_by_cost[-1]
            fallback = sorted_by_cost[:-1][::-1]
            reason = f"Reasoning task '{task}': selecting highest-capability model"
        else:
            selected = sorted_by_cost[0]
            fallback = sorted_by_cost[1:]
            reason = f"Simple task '{task}': selecting lowest-cost model"

        return RoutingDecision(
            model=selected,
            strategy_used=self.name,
            reason=reason,
            fallback_chain=fallback,
        )

    def _classify_task(self, prompt: str) -> str:
        # TODO: implement lightweight task classifier (keyword heuristic first, then LLM)
        return "simple"
