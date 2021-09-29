from __future__ import annotations

from operator import attrgetter
from typing import Generic, Optional, TypeVar, Union

from uprate.store import BaseStore, MemoryStore

from .errors import RateLimitError
from .rate import Rate, _RateGroup

__all__ = (
    "RateLimit"
)

H = TypeVar("H")
"""A TypeVar"""


class RateLimit(Generic[H]):
    """Enforces multiple rates per provided keys.
    This is a low-level component.

    Attributes
    ----------
    rates : tuple[:class:`uprate.rate.Rate`]
        A tuple of :class:`uprate.rate.Rate` sorted in ascending order by the rate's
        time period.

    store: Optional[BaseStore]
        The Store in use for this RateLimit.
    """
    rates: tuple[Rate, ...]
    store: BaseStore[H]

    def __init__(self, rate: Union[Rate, _RateGroup], store: Optional[BaseStore[H]] = None) -> None:
        """Constructor for :class:`.RateLimit`

        Parameters
        ----------
        rate: Union[:class:`uprate.rate.Rate`, :class:`uprate.rate._RateGroup`]
            The rate(s) to enforce on keys in this ratelimits.

        store: Optional[BaseStore]
            The Store to use for this RateLimit, If None then a :class:`uprate.store.MemoryStore` is used.
            By default, :data:`None`.

        Raises
        ------
        :exc:`TypeError`
            ``rate`` parameter provided to the constructor is of invalid type.
        """
        if isinstance(rate, Rate):
            self.rates = (rate,)
        elif isinstance(rate, _RateGroup):
            rate._data.sort(key=attrgetter("period"))
            self.rates = tuple(rate._data)
        else:
            raise TypeError(f"Expected instance of uprate.rate.Rate or uprate.rate._RateGroup Instead got {type(rate)}")

        if store is None:
            self.store = MemoryStore()
        elif isinstance(store, BaseStore):
            self.store = store
        else:
            raise TypeError("Expected a type deriving from uprate.store.BaseStore instead got " + str(type(store)))

        self.store.setup(self)

    async def acquire(self, key: H) -> None:
        """Try to acquire a usage token for given token.
        Raise an error if token can't be acquired

        Parameters
        ----------
        key : :data:`.H`
            The key to acquire a usage token for.

        Returns
        -------
        :data:`None`
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
        key : Optional[:data:`None`]
            The key to reset ratelimit for. If :data:`None`, then resets all ratelimits, by default :data:`None`.

        Returns
        -------
        :data:`None`
        """
        if not key:
            await self.store.clear()
        else:
            await self.store.reset(key)
