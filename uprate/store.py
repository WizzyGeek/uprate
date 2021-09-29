from __future__ import annotations

from abc import abstractmethod
from collections.abc import Hashable
from time import monotonic as _now
from typing import (TYPE_CHECKING, Optional, Protocol, TypeVar, Union,
                    runtime_checkable)

if TYPE_CHECKING:
    from .rate import Rate
    from .ratelimit import RateLimit

__all__ = (
    "BaseStore",
    "MemoryStore"
)

T = TypeVar("T", contravariant=True)
H = TypeVar("H", contravariant=True, bound=Hashable)

@runtime_checkable
class BaseStore(Protocol[T]):
    limit: RateLimit

    def setup(self, ratelimit: RateLimit):
        """Adds the ratelimit that this store is bound to as an
        attribute under :attr:`.BaseStore.limit`. This method exists
        only to create a circular reference between the store and ratelimit.
        :attr:`uprate.RateLimit.rates` attribute allows the store to access
        all implemented rates.

        Parameters
        ----------
        ratelimit : RateLimit
            The ratelimit which this store is bound to.
        """
        self.limit = ratelimit

    @abstractmethod
    async def acquire(self, key: T) -> tuple[bool, float, Optional[Rate]]:
        """Try to acquire a usage token for given key.

        .. note::
            To get all the rates that this key follows use
            .. code-block:: python

                self.limit.rates

        .. note::
            If a HashMap like data-structure is being nested, then it's best that it is nested by
            the rates instead of the keys, since the number of keys may not exceed 1 in most cases,
            while the number of keys could grow upto 100k or more fairly quickly.

        Parameters
        ----------
        key : :data:`uprate.store.T`
            The key to acquire a ratelimit for.

        Returns
        -------
        tuple[:class:`bool`, :class:`float`, Optional[:class:`uprate.rate.Rate`]]
            A three element tuple, the first element of type :class:`bool` depicting success.

            Second element :class:`float` which is the amount of time to retry in, If a usage
            token was acquired this should return ``0`` other-wise the time in which a
            usage token will be available. If the store does not support retry time then it
            should return a negative value like ``-1`` (negative values shall be returned only on
            failure if the retry time cannot be determined).

            The last element is the :class:`uprate.rate.Rate` object which was violated,
            this must be the rate which will take the longest to reset. The last element is
            expected to be :data:`None` if acquiring was successfull.
        """
        ...

    @abstractmethod
    async def reset(self, key: T) -> None:
        """Reset the usage tokens for given key.
        Implementation wise, deleting all the records for the given key should be enough.

        Parameters
        ----------
        key : :data:`uprate.store.T`
            The key to acquire a ratelimit for.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Reset all the keys in the store.

        Returns
        -------
        :data:`None`
        """
        ...

class MemoryStore(BaseStore[H]):
    _data: dict[H, tuple[list[Union[int, float]], ...]]

    def __init__(self):
        self._data = {}
        self._last_verified = 0.0
        self.limit = 0

    def setup(self, ratelimit: RateLimit):
        super().setup(ratelimit)
        self._max_period = self.limit.rates[-1].period

    async def acquire(self, key: H) -> tuple[bool, float, Optional[Rate]]:
        now = _now()
        self.verify_cache() # Evict stale keys
        record = self._data.get(key, None)

        if record is None:
            # 1st insert
            self._data[key] = tuple([i.uses - 1, now] for i in self.limit.rates)
            return True, 0.0, None
        else:
            worst: float = False
            worst_rate: Optional[Rate] = None

            for use_dt, rate in zip(record, self.limit.rates):
                if use_dt[0] == 0:
                    if (then := (use_dt[1] + rate.period)) <= now:
                        use_dt[:] = [rate.uses - 1, now]
                    elif (retry := then - now) > worst:
                        worst = retry
                        worst_rate = rate
                else:
                    use_dt[0] -= 1
            if worst is False:
                return True, 0.0, None

            return False, worst, worst_rate

    async def reset(self, key: H) -> None:
        del self._data[key]

    async def clear(self) -> None:
        self._data.clear()

    def verify_cache(self) -> None:
        # There is no way something has expired since the last
        # check if enough time hasn't passed.
        if (_now() - self._last_verified) < self._max_period:
            return

        now = _now()
        delete = list[H]()

        for k, v in self._data.items():
            if self._max_period < (now - v[-1][1]):
                delete.append(k)

        for i in delete:
            del self._data[i]
