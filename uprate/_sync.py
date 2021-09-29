"""Low-level internal syncronous API"""

# We could have just made it so that one API handles both by returning awaitables when
# async stores are used, although that increaseas type unsafety and as of now does not play well
# with type checkers
from __future__ import annotations

from abc import abstractmethod
from operator import attrgetter
from time import monotonic as _now
from typing import (TYPE_CHECKING, Generic, Optional, Protocol, TypeVar, Union,
                    runtime_checkable)

from .errors import RateLimitError
from .rate import Rate, _RateGroup
from .store import H, T

G = TypeVar("G")

if TYPE_CHECKING:
    from .rate import Rate, _RateGroup

@runtime_checkable
class SyncStore(Protocol[T]):
    limit: SyncRateLimit

    def setup(self, ratelimit: SyncRateLimit):
        """Same as :method:`uprate.BaseStore.setup`"""
        self.limit = ratelimit

    @abstractmethod
    def acquire(self, key: T) -> tuple[bool, float, Optional[Rate]]:
        """Sync version of :abstractmethod:`uprate.BaseStore.acquire`"""
        ...

    @abstractmethod
    def reset(self, key: T) -> None:
        """Sync version of :abstractmethod:`uprate.BaseStore.reset`"""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Sync version of :abstractmethod:`uprate.BaseStore.clear`"""
        ...

class SyncMemoryStore(SyncStore[H]):
    _data: dict[H, tuple[list[Union[int, float]], ...]]

    def __init__(self):
        self._data = {}
        self._last_verified = 0.0
        self.limit = 0

    def setup(self, ratelimit: SyncRateLimit):
        super().setup(ratelimit)
        self._max_period = self.limit.rates[-1].period

    def acquire(self, key: H) -> tuple[bool, float, Optional[Rate]]:
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

    def reset(self, key: H) -> None:
        del self._data[key]

    def clear(self) -> None:
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

class SyncRateLimit(Generic[G]):
    """Enforces multiple rates per provided keys.
    This is a low-level sync component.
    Sync version of :class:`uprate.RateLimit`

    Attributes
    ----------
    rates : tuple[:class:`uprate.rate.Rate`]
        A tuple of :class:`uprate.rate.Rate` sorted in ascending order by the rate's
        time period.
    """
    rates: tuple[Rate, ...]
    store: SyncStore[G]

    def __init__(self, rate: Union[Rate, _RateGroup], store: Optional[SyncStore[G]] = None) -> None:
        if isinstance(rate, Rate):
            self.rates = (rate,)
        elif isinstance(rate, _RateGroup):
            rate._data.sort(key=attrgetter("period"))
            self.rates = tuple(rate._data)
        else:
            raise TypeError(f"Expected instance of uprate.rate.Rate or uprate.rate._RateGroup Instead got {type(rate)}")

        if store is None:
            self.store = SyncMemoryStore()
        elif isinstance(store, SyncStore):
            self.store = store
        else:
            raise TypeError("Expected a type deriving from uprate.store.SyncStore instead got " + str(type(store)))

        self.store.setup(self)

    def acquire(self, key: G) -> None:
        res, retry, rate = self.store.acquire(key)

        if not res:
            # <../ratelimit.py#81>
            raise RateLimitError(retry_after=retry, rate=rate) # type: ignore[arg-type]

    def reset(self, key: G = None) -> None:
        if not key:
            self.store.clear()
        else:
            self.store.reset(key)
