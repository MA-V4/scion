from __future__ import annotations

import pytest
from httpx import AsyncClient
from gateway.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_models_endpoint_returns_list():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/v1/models")
    assert resp.status_code == 200
    assert "data" in resp.json()
