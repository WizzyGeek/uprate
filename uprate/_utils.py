from __future__ import annotations

from inspect import isawaitable
from typing import Awaitable, TypeVar, Union
from time import time_ns, monotonic_ns

R = TypeVar("R")

__all__ = (
    "maybe_awaitable",
)

async def maybe_awaitable(ret: Union[R, Awaitable[R]]) -> R:
    if isawaitable(ret): # Type Guard Problem here
        return await ret # type: ignore[misc]
    else:
        return ret # type: ignore[return-value]

def monotonic_to_unix(time_sec: float) -> float:
    """Convert to UNIX timestamp according to current time on device"""
    uts, mts = time_ns(), monotonic_ns()
    return ((uts - mts) / 1e9) + time_sec