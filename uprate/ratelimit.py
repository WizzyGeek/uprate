from __future__ import annotations

from operator import attrgetter
from typing import Optional, Union, Generic, TypeVar, overload
from collections.abc import Hashable

from .rate import Rate, _RateGroup, _now

H = TypeVar("H", bound=Hashable)
"""A TypeVar bound to :class:`collections.abc.Hashable`"""

_AlwaysGreater = type(
    "AlwaysGreater", (float,), {
        "__gt__": lambda _, o: True,
        "__lt__": lambda _, o: False
})(0)

class UsageRecord:
    """Enforces a single rate on usage. You should probably
    interact with :class:`.Usage` objects if you do not want to deal
    with each rate in a ratelimit.

    Attributes
    ----------
    uses_left : :class:`int`
        The number on usage tokens left for the enforced rate.
    previous_reset : :class:`float`
        Timestamp of the of the last reset.
    rate : :class:`uprate.rate.Rate`
        The enforced :class:`uprate.rate.Rate` object.
    """
    __slots__ = (
        "uses_left",
        "previous_reset",
        "rate"
    )

    uses_left: int
    previous_reset: float
    rate: Rate

    def __init__(self, rate: Rate, now: float =  None) -> None:
        self.uses_left = rate.uses
        self.previous_reset = now or _now()
        self.rate = rate

    # Acquiring a single rate will break other ratelimits.
    # def acquire(self): ...

    def reset(self: UsageRecord, now: float = None) -> None:
        """Reset the period and the usage tokens.
        If this is used with :class:`.Usage` then you should use
        :meth:`.Usage.reset` instead to keep other rates from breaking.

        Parameters
        ----------
        now : Optional[:class:`float`]
            The current timestamp in seconds.
            If :data:`None`, get current timestamp, by default :data:`None`
        """
        self.previous_reset = now or _now()
        self.uses_left = self.rate.uses

    def retry_after(self, now: float = None) -> float:
        """Return the amount of time in which a usage token will be available for use

        Parameters
        ----------
        now : Optional[:class:`float`]
            The current timestamp in seconds.
            If :data:`None`, get current timestamp, by default :data:`None`

        Returns
        -------
        :class:`float`
            The time in seconds, after which usage token will be available. This is never negative.
        """
        return min(0.0, self.rate.period + self.previous_reset - (now or _now()))


class Usage:
    """Tracks usage for enforcing multiple rates.

    Attributes
    ----------
    usages : tuple[:class:`.UsageRecord`, ...]
        A tuple of :class:`.UsageRecord` objects used for enforcing multiple rates.
    """
    __slots__ = ("usages",)

    usages: tuple[UsageRecord, ...]

    def __init__(self, rates: tuple[Rate, ...]) -> None:
        now = _now()
        # ensure rates are sorted
        self.usages = tuple(UsageRecord(i, now) for i in sorted(rates, key=attrgetter("period")))

    def acquire(self) -> bool:
        """Try to to acquire a usage token while satisfying all rates.

        Returns
        -------
        :class:`bool`
            Whether a usage token was acquired or not.
        """
        now = _now()

        for rec in self.usages:
            delta = now - rec.previous_reset

            if delta > rec.rate.period:
                rec.reset(now)

            rec.uses_left -= 1

            if (rec.uses_left) < 0:
                rec.uses_left = -1
                return False
        return True

    def reset(self, now: float = None) -> None:
        """Reset the period and the usage tokens for all rates.

        Parameters
        ----------
        now : Optional[:class:`float`]
            The current timestamp in seconds.
            If :data:`None`, get current timestamp, by default :data:`None`
        """
        for rec in self.usages:
            rec.reset(now)

    def retry_after(self, now: float = None) -> float:
        """Return the amount of time in which a usage token will be available for use.
        Same as :class:`.UsageRecord` only difference is that, this considers all applied rates.

        Parameters
        ----------
        now : Optional[:class:`float`]
            The current timestamp in seconds.
            If :data:`None`, get current timestamp, by default :data:`None`

        Returns
        -------
        float
            The time in seconds, after which usage token will be available. This is never negative.
        """
        highest: float = 0.0
        for i in self.usages:
            tmp = i.retry_after(now)
            highest = max(highest, tmp)

        return highest

    def stale(self, now: float = None, accurate: bool = False) -> float:
        """How long the ratelimits have been inactive for.

        Parameters
        ----------
        now : Optional[:class:`float`]
            The current timestamp in seconds.
            If :data:`None`, get current timestamp, by default :data:`None`
        accurate : :class:`bool`
            Whether to check all enforced rates or not.
            Normally checking the longest rate should be enough,
            if none of the enforced rates have been resetted individually.

        Returns
        -------
        :class:`float`
            For how long the enforced ratelimits have been inactive. A negative number signifies
            that the enforced ratelimits are active and will become stale in that time.
        """
        # We return staleness of the longest enforced rate.
        now = now or _now()

        # If some rate other than longest was reset individually
        if accurate:
            lowest: float = _AlwaysGreater
            for rec in self.usages:
                stale_for = now - rec.rate.period - rec.previous_reset
                lowest = min(stale_for, lowest)
            return lowest

        rec = self.usages[-1]
        return now - rec.rate.period - rec.previous_reset

class RateLimit(Generic[H]):
    """Enforces ratelimits per multiple keys

    Attributes
    ----------
    rates : tuple[:class:`uprate.rate.Rate`]
        A tuple of :class:`uprate.rate.Rate` sorted in ascending order by the rate's
        time period.
    """
    rates: tuple[Rate, ...]
    _cache: dict[Optional[H], Usage]

    def __init__(self, rate: Union[Rate, _RateGroup]) -> None:
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

        self._cache = {}

    @overload
    def acquire(self) -> bool:
        ...

    @overload
    def acquire(self, key: H) -> bool:
        ...

    def acquire(self, key = None):
        """Acquire a usage token for given token

        Parameters
        ----------
        key : Optional[:data:`.H`]
            The key to acquire a usage token for, if :data:`None`, by default :data:`None`

        Returns
        -------
        :class:`bool`
            Wether a usage token was aqcuired or not.
        """
        if key in self._cache:
            return self._cache[key].acquire()

        self._cache[key] = usage = Usage(self.rates)
        return usage.acquire()

    def reset(self, key: H = None) -> None:
        """Reset the given key.

        Parameters
        ----------
        key : Optional[:data:`None`]
            The key to reset ratelimit for. If :data:`None`, then resets all ratelimits, by default :data:`None`.

        Returns
        -------
        :data:`None`
        """
        if key is None:
            self._cache.clear()
            return None
        del self._cache[key]

