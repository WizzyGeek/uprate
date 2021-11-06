from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from .errors import RateLimitError
from .ratelimit import RateLimit

if TYPE_CHECKING:
    from .store import BaseStore
    from .rate import Rate, RateGroup

    from types import TracebackType

__all__ = (
    "Bucket",
)

T = TypeVar("T")

class BucketCM(Generic[T]):
    key: T
    bucket: Bucket[T]

    def __init__(self, bucket: Bucket[T], key: T):
        self.bucket = bucket
        self.key = key

    async def __aenter__(self):
        if self.bucket._queue:
            await self.bucket._queue.get()

        await self.__wait()
        return None

    async def __aexit__(self,
                        exc_type: type[BaseException] | None,
                        exc: BaseException | None,
                        tb: TracebackType | None) -> Literal[False]:
        if self.bucket._queue:
            self.bucket._queue.put_nowait(None)

        return False

    async def __wait(self) -> None:
        while True:
            try:
                await self.bucket._limit.acquire(self.key)
            except RateLimitError as err:
                await asyncio.sleep(float(err))
            else:
                return None

class Bucket(Generic[T]):
    """A high level ratelimit construct to obey both
    ratelimits and concurrency.

    .. note::

        Unlike other constructs in uprate, :class:`.Bucket` does not have
        a sync counterpart for threaded applications, a sync counterpart maybe
        added with enough interest.

    Parameters
    ----------
    rate : :class:`~uprate.rate.Rate`, :class:`~uprate.rate.RateGroup`, (``Rate | RateGroup``)
        The rate(s) to enforce on keys in this bucket.
    store : :class:`~uprate.store.BaseStore`, (``BaseStore | None``)
        The store to use for the under lying :class:`~uprate.ratelimit.RateLimit`. By default, :data:`None`.
    concurrency : :class:`int`
        The number of concurrently executing acquires/context managers.
        If ``0`` or lower then only the ratelimit is enforced.
        By default, ``0``
    """

    _limit: RateLimit[T]
    _queue: asyncio.Queue | None

    def __init__(self, rate: Rate | RateGroup, store: BaseStore[T] = None, concurrency: int = 0) -> None:
        self._limit = RateLimit(rate, store)

        if concurrency > 0:
            self._queue = asyncio.Queue(maxsize=concurrency)

            for _ in range(concurrency):
                self._queue.put_nowait(None)
        else:
            self._queue = None

    @classmethod
    def from_limit(cls, limit: RateLimit[T]) -> Bucket[T]:
        """Create a bucket from a :class:`~uprate.ratelimit.RateLimit`

        Parameters
        ----------
        limit : :class:`~uprate.ratelimit.RateLimit`
            The ratelimit to create a :class:`.Bucket` from.
            The provided ratelimit is used as it is, hence mutating it wil
            also affect the bucket

        Returns
        -------
        :class:`.Bucket`
            The created bucket
        """
        self = object.__new__(cls)
        self.limit = limit
        return self

    def acquire(self, key: T) -> BucketCM[T]:
        """Return an async context manager which
        tries to acquire a usage token upon entering while
        respecting the concurrency limit.

        Parameters
        ----------
        key : :data:`.T`
            The key to acquire.

        Returns
        -------
        :class:`uprate.bucket.BucketCM`
            The async context manager for the key.

        Example
        -------

        .. code-block:: python3

            bucket: Bucket[str] = Bucket(30 / Seconds(1), concurrency=1)
            ...
            # Wait until concurrency and ratelimit are satisfied.
            async with bucket.acquire("key"):
                ...
        """
        return BucketCM(self, key)

    async def reset(self, key: T = None) -> None:
        """Reset the given key.

        Parameters
        ----------
        key : :data:`.T`, :data:`None`, (``T | None``)
            The key to reset ratelimit for. If :data:`None`, then resets all ratelimits, by default :data:`None`.
        """
        self._limit.reset()

    @property
    def rates(self) -> tuple[Rate, ...]:
        """tuple[:class:`~uprate.rate.Rate`] : Same as :attr:`.RateLimit.rates`"""
        return self._limit.rates

    @property
    def store(self) -> BaseStore:
        """:class:`~uprate.store.BaseStore` : Same as :attr:`.RateLimit.store`"""
        return self._limit.store
