from __future__ import annotations

from operator import attrgetter
from typing import Generic, Optional, TypeVar, Union

from uprate.store import BaseStore, MemoryStore

from .errors import RateLimitError
from .rate import Rate, RateGroup

__all__ = (
    "RateLimit",
)

H = TypeVar("H")
"""A TypeVar"""

class RateLimit(Generic[H]):
    """Enforces multiple rates per provided keys.
    This is a low-level component.

    Parameters
    ----------
    rate: :class:`~uprate.rate.Rate`, :class:`~uprate.rate.RateGroup`, (``Rate | RateGroup``)
        The rate(s) to enforce on keys in this ratelimits.

    store: :class:`~uprate.store.BaseStore`, (``BaseStore | None``)
        The store to use for this RateLimit, If None then a :class:`uprate.store.MemoryStore` is used.
        By default, :data:`None`.

    Raises
    ------
    :exc:`TypeError`
        ``rate`` parameter provided to the constructor is of invalid type.

    Attributes
    ----------
    rates : tuple[:class:`uprate.rate.Rate`]
        A tuple of :class:`uprate.rate.Rate` sorted in ascending order by the rate's
        time period.
    store : :class:`~uprate.store.BaseStore`
        The store in use for this RateLimit.
    """
    rates: tuple[Rate, ...]
    store: BaseStore[H]

    def __init__(self, rate: Union[Rate, RateGroup], store: Optional[BaseStore[H]] = None) -> None:
        if isinstance(rate, Rate):
            self.rates = (rate,)
        elif isinstance(rate, RateGroup):
            rate._data.sort(key=attrgetter("period"))
            self.rates = tuple(rate._data)
        else:
            raise TypeError(f"Expected instance of uprate.rate.Rate or uprate.rate.RateGroup Instead got {type(rate)}")

        if store is None:
            self.store = MemoryStore()
        elif isinstance(store, BaseStore):
            self.store = store
        else:
            raise TypeError("Expected a type deriving from uprate.store.BaseStore instead got " + str(type(store)))

        self.store.setup(self)

    async def acquire(self, key: H) -> None:
        """Try to acquire a usage token for given token.
        Raise an error if token can't be acquired.

        Parameters
        ----------
        key : :data:`.H`
            The key to acquire a usage token for.

        Raises
        ------
        :exc:`~uprate.errors.RateLimitError`
            Cannot acquire usage token due to exhaustion.
        """
        res, retry, rate = await self.store.acquire(key)

        if not res:
            # cast is ugly, overloads don't work (parameters don't change)
            # TODO: https://www.python.org/dev/peps/pep-0647/
            raise RateLimitError(retry_after=retry, rate=rate) # type: ignore[arg-type]

    async def reset(self, key: H = None) -> None:
        """Reset the given key.

        Parameters
        ----------
        key : :data:`.H`, :data:`None`, (``H | None``)
            The key to reset ratelimit for. If :data:`None`, then resets all ratelimits, by default :data:`None`.
        """
        if not key:
            await self.store.clear()
        else:
            await self.store.reset(key)
