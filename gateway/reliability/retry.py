from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, TypeVar

T = TypeVar("T")


async def with_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 10.0,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff and full jitter.
    Raises the last exception if all attempts fail.
    """
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            delay = min(max_delay_s, base_delay_s * (2 ** attempt))
            jitter = random.uniform(0, delay)
            await asyncio.sleep(jitter)

    raise last_exc or RuntimeError("All retry attempts failed")
