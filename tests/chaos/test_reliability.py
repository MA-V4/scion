from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_circuit_breaker_prevents_cascade_on_backend_failure():
    # TODO: mock a backend that returns errors
    # Verify: circuit opens after N failures, requests are rejected fast
    # Verify: circuit attempts recovery after timeout
    pass


@pytest.mark.asyncio
async def test_retry_does_not_cause_storm():
    # TODO: mock a backend that fails then recovers
    # Verify: retry with jitter limits total request volume during failure window
    pass
