from __future__ import annotations

import pytest
from gateway.routing.registry import ModelRegistry
from gateway.routing.router import ModelRouter, RoutingContext
from gateway.routing.strategies.round_robin import RoundRobinStrategy
from gateway.routing.strategies.cost_aware import CostAwareStrategy


@pytest.mark.asyncio
async def test_round_robin_cycles_through_models():
    # TODO: set up registry with 3 models, verify round robin selects each in turn
    pass


@pytest.mark.asyncio
async def test_cost_aware_routes_simple_to_cheapest():
    # TODO: verify CostAwareStrategy selects cheapest model for a simple task
    pass


@pytest.mark.asyncio
async def test_router_raises_when_no_healthy_models():
    # TODO: mark all models as unhealthy, verify RuntimeError is raised
    pass
