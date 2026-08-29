from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from gateway.api.routes import router
from gateway.config import settings
from gateway.middleware.auth import APIKeyMiddleware
from gateway.middleware.rate_limit import RateLimitMiddleware
from gateway.middleware.tracing import TracingMiddleware
from gateway.reliability.circuit_breaker import CircuitBreakerRegistry
from gateway.routing.registry import ModelRegistry
from gateway.routing.router import ModelRouter
from gateway.routing.strategies.round_robin import RoundRobinStrategy
from serving.backends.factory import BackendFactory

log = structlog.get_logger()

registry = ModelRegistry()
factory = BackendFactory()
router_instance = ModelRouter(registry=registry, strategy=RoundRobinStrategy())
circuit_breakers = CircuitBreakerRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("scion.gateway.starting", env=settings.env, port=settings.port)
    registry.load_from_yaml(settings.models_config_path)
    log.info("scion.gateway.models_loaded", count=len(registry.all()))
    yield
    await factory.close_all()
    log.info("scion.gateway.stopped")


app = FastAPI(
    title="Scion LLM Gateway",
    description="OpenAI-compatible LLM gateway with intelligent routing and full observability",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    APIKeyMiddleware,
    valid_keys=set(),
    dev_mode=settings.env == "development",
)
app.add_middleware(TracingMiddleware)

app.include_router(router)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health() -> dict:
    models = [{"name": m.name, "healthy": m.health.is_healthy} for m in registry.all()]
    return {
        "status": "ok",
        "version": "0.1.0",
        "models": models,
        "circuit_breakers": circuit_breakers.status(),
    }