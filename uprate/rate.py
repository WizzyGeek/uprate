from __future__ import annotations

from time import monotonic as _now

__all__ = (
    "Rate",
    "Seconds",
    ""
)

class Rate:
    """A rate consisting of uses and time period

    Used to define rates for ratelimits
    with syntatical expressions.
    """
    def __init__(self, uses: int, period: float) -> None:
        self.uses = uses
        self.period = period

    def __call__(self, magnitude: float) -> Rate:
        return self.__class__(self.uses, self.period * magnitude)

    def __rtruediv__(self, other: int) -> Rate:
        return self.__class__(other, self.period)

    def __or__(self, other: Rate) -> tuple[Rate, Rate]:
        # We dont want other.__ror__ to be called.
        if not isinstance(other, self.__class__):
            raise TypeError(f"unsupported operand type(s) for |: '{self.__class__}' and '{type(other)}'")
        return self, other

    __ror__ = __or__

    def __mul__(self, other: int) -> Rate:
        if isinstance(other, int):
            return self.__class__(self.uses, self.period * other)
        return NotImplemented

    __rmul__ = __mul__

    def __add__(self, other: Rate) -> Rate:
        if isinstance(other, self.__class__):
            if other.uses != 1 or self.uses != 1:
                raise ValueError("Cannot 'add' two rates which have uses other than one")
            return self.__class__(1, self.period + other.period)
        return NotImplemented

    __radd__ = __add__

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.period == other.period and self.uses == other.uses
        return NotImplemented

    def __ne__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return not (self == other)
        return False


"""A Rate of 1 use / 1 Second
Used in syntatical expression to define rate

Example
-------
::py

    assert 2 / Seconds(3) == 2 / (3 * Seconds)
    ...
    # 30 uses per 2 min 30 sec but also 2 uses per 2 seconds
    api_rate: tuple[Rate] = 2/Seconds(2) | 30/(2 * Minutes + 30 * seconds)

"""
Seconds = Rate(1, 1)

"""Rate of 1 use / 1 Minute"""
Minutes = 60 * Seconds

"""Rate of 1 use / 1 Hour"""
Hours = 60 * Minutes

"""Rate of 1 use / 1 Day"""
Days = 24 * Hours

"""Rate of 1 use / 1 Week"""
Weeks = 7 * Days

"""Rate of 1 use / 1 Month

.. note::

    If you need larger time periods you can create them by
    ::py

        Year = Rate(1, 60 * 60 * 24 * 365)
        # Proceed to use like other unitary use rates
        rate = 5 / Year(2) # 5 uses per 2 years

"""
Months = 30 * Days
