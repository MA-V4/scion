from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any

import httpx


async def with_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 15.0,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff and full jitter.
    Handles 429 rate limit responses with a longer wait.
    """
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await fn(*args, **kwargs)
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code == 429:
                retry_after = float(exc.response.headers.get("retry-after", 5))
                await asyncio.sleep(retry_after + random.uniform(0, 1))
            elif attempt == max_attempts - 1:
                break
            else:
                delay = min(max_delay_s, base_delay_s * (2**attempt))
                jitter = random.uniform(0, delay)
                await asyncio.sleep(jitter)
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            delay = min(max_delay_s, base_delay_s * (2**attempt))
            jitter = random.uniform(0, delay)
            await asyncio.sleep(jitter)

    raise last_exc or RuntimeError("All retry attempts failed")
