from __future__ import annotations

from typing import Union, Optional

__all__ = (
    "Rate",
    "Seconds",
    "Minutes",
    "Hours",
    "Days",
    "Weeks",
    "Months"
)

class _RateGroup:
    __slots__ = ("_data",)

    _data: list[Rate]

    def __init__(self):
        self._data = []

    def __or__(self, other) -> _RateGroup:
        if isinstance(other, Rate):
            self._data.append(other)
            return self
        elif isinstance(other, self.__class__):
            self._data = self._data + other._data
            return self
        return NotImplemented

    # __ror__ wouldn't be called
    # unless someone is using it wrong or
    # is dealing with uprate's internals
    __ror__ = __or__


class Rate:
    """A rate consisting of uses and time period

    Used to define rates for ratelimits
    with syntatical expressions.

    You should refrain from creating your own Rate objects
    and instead use the objects provided in the library.

    Attributes
    ----------
    uses: int
        Number of uses per time period
    period: float
        The time period of the rate in seconds
    """
    __slots__ = ("uses", "period")

    uses: int
    period: float

    def __init__(self, uses: int, period: float) -> None:
        self.uses = uses
        self.period = period

    def __call__(self, magnitude: float) -> Rate:
        return self.__class__(self.uses, self.period * magnitude)

    def __or__(self, other: Union[Rate, _RateGroup]) -> _RateGroup:
        if isinstance(other, _RateGroup):
            return other | self
        elif isinstance(other, self.__class__):
            return _RateGroup() | self | other
        return NotImplemented

    __ror__ = __or__

    def __rtruediv__(self, other: int) -> Rate:
        return self.__class__(other, self.period)

    def __mul__(self, other: float) -> Rate:
        # Let multipling a Rate increase the time period
        if isinstance(other, (float, int)):
            return self.__class__(self.uses, self.period * other)
        return NotImplemented

    __rmul__ = __mul__

    def __truediv__(self, other: float) -> Rate:
        # Let dividing a Rate decrease the time period
        if isinstance(other, (float, int)):
            return self.__class__(self.uses, self.period / other)
        return NotImplemented

    def __add__(self, other: Rate) -> Rate:
        if isinstance(other, self.__class__):
            if other.uses != 1 or self.uses != 1:
                raise ValueError("Cannot 'add' two rates which have uses other than one")
            return self.__class__(1, self.period + other.period)
        return NotImplemented

    __radd__ = __add__

    # object has other as object / Liskov Principle

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.period == other.period and self.uses == other.uses
        return NotImplemented

    def __ne__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return not (self == other)
        return False

    def __hash__(self) -> int:
        # This might be a bad idea
        return hash((self.uses, self.period))

    def __str__(self) -> str:
        return f"{self.uses}/{self.period}"


Seconds = Rate(1, 1)
"""A Rate of 1 use / 1 Second
Used in syntatical expression to define rate

Example
-------
.. code-block:: python

    assert 2 / Seconds(3) == 2 / (3 * Seconds)
    ...
    # 30 uses per 2 min 30 sec but also 2 uses per 2 seconds
    api_rate: uprate.rate._RateGroup = 2/Seconds(2) | 30/(2 * Minutes + 30 * seconds)

"""

Minutes = 60 * Seconds
"""Rate of 1 use / 1 Minute"""

Hours = 60 * Minutes
"""Rate of 1 use / 1 Hour"""

Days = 24 * Hours
"""Rate of 1 use / 1 Day"""

Weeks = 7 * Days
"""Rate of 1 use / 1 Week"""

Months = 30 * Days
"""Rate of 1 use / 1 Month


Note
----
If you need larger time periods you can create them by

.. code-block:: python

    Year = Rate(1, 60 * 60 * 24 * 365)
    # Proceed to use like other unitary use rates
    rate = 5 / Year(2) # 5 uses per 2 years

"""
