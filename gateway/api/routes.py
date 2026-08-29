from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from gateway.models.request import LLMRequest, LLMResponse
from gateway.reliability.circuit_breaker import CircuitBreaker
from gateway.reliability.retry import with_retry
from gateway.streaming.sse import stream_sse
from observability.metrics.prometheus import (
    cost_total,
    request_latency,
    request_total,
    tokens_total,
)

router = APIRouter()


async def _invoke(backend, request: LLMRequest, timeout_s: float = 30.0) -> LLMResponse:
    """Call backend.generate with timeout and retry."""
    async with asyncio.timeout(timeout_s):
        return await with_retry(backend.generate, request, max_attempts=3)


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(request: Request, body: LLMRequest) -> LLMResponse | StreamingResponse:
    from gateway.main import circuit_breakers, factory, registry, router_instance

    trace_id = request.state.trace_id
    start = time.time()

    # If the model name matches a registered model exactly, use it directly.
    # Otherwise, treat it as a routing hint and let the router decide.
    try:
        explicit_model = registry.get(body.model)
        models_to_try = [explicit_model]
    except KeyError:
        try:
            decision = await router_instance.route(body)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        models_to_try = [decision.model] + decision.fallback_chain

    last_error: Exception | None = None

    for model in models_to_try:
        cb: CircuitBreaker = circuit_breakers.get(model.name)

        if not cb.is_available():
            continue

        backend = factory.get(model)

        try:
            if body.stream:
                chunks = backend.stream(body)
                return StreamingResponse(
                    stream_sse(chunks),
                    media_type="text/event-stream",
                    headers={"X-Trace-ID": trace_id},
                )

            response = await _invoke(backend, body)
            cb.record_success()

            latency = time.time() - start
            request_total.labels(model=model.name, status="success").inc()
            request_latency.labels(model=model.name).observe(latency)
            tokens_total.labels(model=model.name, type="input").inc(response.usage.prompt_tokens)
            tokens_total.labels(model=model.name, type="output").inc(response.usage.completion_tokens)
            cost = (
                response.usage.prompt_tokens / 1_000_000 * model.cost_per_1m_input
                + response.usage.completion_tokens / 1_000_000 * model.cost_per_1m_output
            )
            cost_total.labels(model=model.name).inc(cost)

            response.trace_id = trace_id
            response.routing_metadata["model_selected"] = model.name
            response.routing_metadata["fallback"] = model.name != models_to_try[0].name
            return response

        except Exception as e:
            import traceback
            cb.record_failure()
            last_error = e
            print(f"Backend {model.name} failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            request_total.labels(model=model.name, status="error").inc()
            continue

    raise HTTPException(
        status_code=503,
        detail=f"All models failed. Last error: {last_error}",
    ) from last_error


@router.get("/v1/models")
async def list_models(request: Request) -> dict:
    from gateway.main import registry

    models = [
        {
            "id": m.name,
            "object": "model",
            "provider": m.provider,
            "context_length": m.context_length,
            "healthy": m.health.is_healthy,
            "capabilities": m.capabilities,
        }
        for m in registry.all()
    ]
    return {"object": "list", "data": models}


@router.get("/v1/usage")
async def usage_summary() -> dict:
    return {"total_tokens": 0, "estimated_cost_usd": 0.0}