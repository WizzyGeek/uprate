from __future__ import annotations

from asyncio import iscoroutinefunction, sleep
from collections.abc import Coroutine
from functools import wraps
from time import sleep as block
from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union

from ._sync import SyncRateLimit, SyncStore
from ._utils import maybe_awaitable
from .errors import RateLimitError
from .ratelimit import RateLimit
from .store import BaseStore

if TYPE_CHECKING:
    from .rate import Rate, _RateGroup

__all__ = (
    "on_retry_sleep",
    "on_retry_block",
    "ratelimit"
)

Key = TypeVar("Key")

async def on_retry_sleep(error: RateLimitError) -> None:
    await sleep(error.retry_after)

def on_retry_block(error: RateLimitError) -> None:
    block(error.retry_after)

def ratelimit(
        rate: Union[Rate, _RateGroup], *,
        key: Callable[..., Union[Key, Coroutine[Any, Any, Key]]] = None,
        on_retry: Callable[[RateLimitError], Union[Any, Coroutine]] = None,
        store: Union[BaseStore, SyncStore] = None
    ) -> Callable:

    def decorator(func):
        nonlocal on_retry
        if iscoroutinefunction(func):
            if isinstance(store, BaseStore) or store is None:
                limit = RateLimit(rate, store)
            else:
                raise TypeError("Cannot use a uprate._sync.SyncStore instance with a coroutine function.")

            @wraps(func)
            async def rated(*args, **kwargs):
                while True:
                    try:
                        bucket = await maybe_awaitable(key(*args, **kwargs))
                        await limit.acquire(bucket)
                    except RateLimitError as err:
                        if on_retry is None:
                            raise err from None
                        else:
                            await maybe_awaitable(on_retry(err))
                    else:
                        return await func(*args, **kwargs)
        else:
            if isinstance(store, SyncStore) or store is None:
                limit = SyncRateLimit(rate, store)
            else:
                raise TypeError("Cannot use a uprate.BaseStore instance with a subroutine.")

            @wraps(func)
            def rated(*args, **kwargs):
                while True:
                    try:
                        bucket = key(*args, **kwargs)
                        limit.acquire(bucket)
                    except RateLimitError as err:
                        if on_retry is None:
                            raise err from None
                        else:
                            on_retry()
                    else:
                        return func()

        rated.limit = limit
        return rated

    return decorator
