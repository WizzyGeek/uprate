from __future__ import annotations

from operator import attrgetter
from typing import Optional, Union, Generic, TypeVar, cast
from collections.abc import Hashable
from uprate.store import BaseStore, MemoryStore

from .rate import Rate, _RateGroup
from .errors import RateLimitError

__all__ = (
    "RateLimit"
)

# This entire thing maybe incompatible with the concept of stores *sigh*

H = TypeVar("H", bound=Hashable)
"""A TypeVar bound to :class:`collections.abc.Hashable`"""


class RateLimit(Generic[H]):
    """Enforces ratelimits per multiple keys

    Attributes
    ----------
    rates : tuple[:class:`uprate.rate.Rate`]
        A tuple of :class:`uprate.rate.Rate` sorted in ascending order by the rate's
        time period.
    """
    rates: tuple[Rate, ...]
    store: BaseStore

    def __init__(self, rate: Union[Rate, _RateGroup], store: Optional[BaseStore] = None) -> None:
        """Constructor for

        Parameters
        ----------
        rate: Union[:class:`uprate.rate.Rate`, :class:`uprate.rate._RateGroup`]
            The rate(s) to enforce on keys in this ratelimits.

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
            # Could use cast here, but it is gross.
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