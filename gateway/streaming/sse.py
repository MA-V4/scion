from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any


async def stream_sse(chunks: AsyncIterator[dict[str, Any]]):
    """
    Format async chunks as Server-Sent Events for streaming responses.
    Each chunk is yielded as 'data: {...}\n\n'. Terminates with 'data: [DONE]\n\n'.
    """
    async for chunk in chunks:
        yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"
