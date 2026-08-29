from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any


async def with_timeout(fn: Callable[..., Any], *args: Any, timeout_s: float, **kwargs: Any) -> Any:
    """Run an async function with a hard timeout. Raises asyncio.TimeoutError on breach."""
    async with asyncio.timeout(timeout_s):
        return await fn(*args, **kwargs)
