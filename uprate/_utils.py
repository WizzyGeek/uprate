from __future__ import annotations

from collections.abc import Coroutine
from inspect import isawaitable
from typing import Awaitable, TypeVar, Union

T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")

__all__ = (
    "maybe_awaitable"
)

def sync_runner(coro: Coroutine[None, None, T_co]) -> T_co:
    """
    .. note:: Don't use with any loop related code.
    """
    try:
        while True:
            coro.send(None)
    except StopIteration as err:
        return err.value
    except BaseException as err:
        raise BaseException from None

async def maybe_awaitable(ret: Union[R, Awaitable[R]]) -> R:
    if isawaitable(ret): # Type Guard Problem here
        return await ret # type: ignore[misc]
    else:
        return ret # type: ignore[return-value]
