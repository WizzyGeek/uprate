from __future__ import annotations

from inspect import isawaitable
from typing import Awaitable, TypeVar, Union

R = TypeVar("R")

__all__ = (
    "maybe_awaitable"
)

async def maybe_awaitable(ret: Union[R, Awaitable[R]]) -> R:
    if isawaitable(ret): # Type Guard Problem here
        return await ret # type: ignore[misc]
    else:
        return ret # type: ignore[return-value]
