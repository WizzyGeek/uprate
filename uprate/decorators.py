from __future__ import annotations

from asyncio import sleep
from inspect import iscoroutinefunction
from collections.abc import Coroutine
from functools import wraps
from time import sleep as block
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ParamSpec,
    Protocol,
    TypeVar,
    Union,
    cast,
    overload,
)

from ._sync import SyncRateLimit, SyncStore
from ._utils import maybe_awaitable
from .errors import RateLimitError
from .ratelimit import RateLimit
from .store import BaseStore
from uprate import _utils

if TYPE_CHECKING:
    from .rate import Rate, RateGroup

__all__ = ("on_retry_sleep", "on_retry_block", "ratelimit")

Key = TypeVar("Key")
"""An unbound and unconstrained TypeVar"""

P = ParamSpec("P")
R = TypeVar("R", covariant=True)

AnyRateLimit = Union[SyncRateLimit, RateLimit]


class LimitedCallable(Protocol[P, R]):
    limit: AnyRateLimit

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> R: ...


def _apply_attrs(func: Callable[P, R], **attrs) -> LimitedCallable[P, R]:
    func = cast(LimitedCallable[P, R], func)

    for k, v in attrs.items():
        setattr(func, k, v)

    return func


async def on_retry_sleep(error: RateLimitError) -> None:
    """Make the current task yield to the event_loop
    till a usage token is available for the rate limit
    which raised :exc:`uprate.errors.RateLimitError`

    Parameters
    ----------
    error : :exc:`.RateLimitError`
        The rate limit error to sleep for.
    """
    await sleep(error.retry_after)


def on_retry_block(error: RateLimitError) -> None:
    """Block the current thread till a usage token is
    available for the rate limit which raised
    :exc:`uprate.errors.RateLimitError`

    Parameters
    ----------
    error : :exc:`.RateLimitError`
        The rate limit error to block for.
    """
    block(error.retry_after)


# TODO: Complete Docs
def ratelimit(
    rate: Rate | RateGroup,
    *,
    key: Callable[..., Key] | Callable[..., Coroutine[Any, Any, Key]] | None = None,
    on_retry: Callable[[RateLimitError], Any]
    | Callable[[RateLimitError], Coroutine]
    | None = None,
    store: BaseStore | SyncStore | None = None,
):
    """Limit a coroutine function or a callable to be called within
    provided rate. :ref:`Example here <index-example>`

    Parameters
    ----------
    rate: :class:`~uprate.rate.Rate`, :class:`~uprate.rate.RateGroup`, (``Rate | RateGroup``)
        The rate that the decorated function must follow.
    key : Callable[..., :data:`.Key`] | Callable[..., Coroutine[Any, Any, :data:`.Key`]] | :data:`None`
        The callback for generating a bucket for ratelimit from the arguments provided
        to the decorated function, this can be a coroutine function only when the decorated
        is a coroutine function as well. If :data:`None`, a default callback returning a string based on the
        decorated function's name is used, by default :data:`None`.
    on_retry : Callable[[:exc:`.RateLimitError`], Any] | Callable[[:exc:`.RateLimitError`], Coroutine] | :data:`None`
        If provided then this function will be called when the function gets ratelimited
        and then the decorated function will be called again, if :data:`None` then function call isn't retried
        and :exc:`.RateLimitError` is raised, by default :data:`None`.
    store : :class:`.BaseStore` | :class:`.SyncStore` | :data:`None`
        The store to use for the rate limit, must be of type :class:`.BaseStore` if
        decorated function is a coroutine function else :class:`.SyncStore`.
        If :data:`None` then a suitable derived memory store is used, by default :data:`None`.

    Raises
    ------
    :exc:`.RateLimitError`
        ``on_retry`` parameter is not provided and the decorated function got ratelimited.
    """
    if TYPE_CHECKING:

        @overload
        def decorator(
            func: Callable[P, Coroutine[Any, Any, R]],
        ) -> LimitedCallable[P, Coroutine[Any, Any, R]]: ...

        @overload
        def decorator(func: Callable[P, R]) -> LimitedCallable[P, R]: ...

    def decorator(func: Callable[..., Any]) -> Any:
        nonlocal on_retry, key
        key_func = key or cast(
            Callable[..., Key],
            lambda *a, **k: (
                "DEFAULT_BUCKET_" + getattr(func, "__name__", "<UNNAMEDCALLABLE>")
            ),
        )

        if iscoroutinefunction(func):
            if (
                (not isinstance(store, SyncStore)) and isinstance(store, BaseStore)
            ) or store is None:
                limit: RateLimit = RateLimit(rate, store)
            else:
                raise TypeError(
                    "Cannot use a uprate._sync.SyncStore instance with a coroutine function."
                )

            @wraps(func)
            async def rated(*args, **kwargs):
                while True:
                    try:
                        bucket = await maybe_awaitable(key_func(*args, **kwargs))
                        await limit.acquire(bucket)
                    except RateLimitError as err:
                        if on_retry is None:
                            raise err from None
                        else:
                            await maybe_awaitable(on_retry(err))
                    else:
                        return await func(*args, **kwargs)

            return _apply_attrs(rated, limit=limit)
        else:
            if isinstance(store, SyncStore) or store is None:
                limit_sync = SyncRateLimit(rate, store)
            else:
                raise TypeError(
                    "Cannot use a uprate.BaseStore instance with a subroutine."
                )

            @wraps(func)
            def rated_sync(*args, **kwargs):
                while True:
                    try:
                        bucket = key_func(*args, **kwargs)
                        limit_sync.acquire(bucket)
                    except RateLimitError as err:
                        if on_retry is None:
                            raise err from None
                        else:
                            on_retry(err)
                    else:
                        return func()

            return _apply_attrs(rated_sync, limit=limit_sync)

    return decorator
