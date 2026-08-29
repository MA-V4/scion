from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from gateway.models.request import LLMRequest, LLMResponse
from gateway.streaming.sse import stream_sse

router = APIRouter()


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(request: Request, body: LLMRequest) -> LLMResponse | StreamingResponse:
    from gateway.main import factory, router_instance

    trace_id = request.state.trace_id

    try:
        decision = await router_instance.route(body)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    backend = factory.get(decision.model)
    body.metadata["trace_id"] = trace_id
    body.metadata["routing_strategy"] = decision.strategy_used
    body.metadata["routing_reason"] = decision.reason

    if body.stream:
        chunks = backend.stream(body)
        return StreamingResponse(
            stream_sse(chunks),
            media_type="text/event-stream",
            headers={"X-Trace-ID": trace_id},
        )

    response = await backend.generate(body)
    response.trace_id = trace_id
    response.routing_metadata["model_selected"] = decision.model.name
    return response


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
    # TODO: query Postgres usage table
    return {"total_tokens": 0, "estimated_cost_usd": 0.0}
