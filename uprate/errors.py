"""Contains all Exception(s) uprate raises
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rate import Rate

__all__ = (
    "RateLimitError",
)

class RateLimitError(Exception):
    """Raised when a Rate Limit is violated.

    Attributes
    ----------
    retry_after : :class:`float`
        The amount of time to retry after in seconds.
    rate : :class:`~uprate.rate.Rate`
        The rate that was violated
    """
    retry_after: float
    rate: Rate

    def __init__(self, retry_after: float, rate: Rate, *args):
        super().__init__(*args)
        self.retry_after = retry_after
        self.rate = rate

    def __float__(self) -> float:
        """Return :attr:`.RateLimitError.retry_after` as a float

        Returns
        -------
        float
            The amount in seconds to retry after.
        """
        return float(self.retry_after)

    def __int__(self) -> int:
        """Return :attr:`.RateLimitError.retry_after` as a ceiled int.

        Returns
        -------
        int
            The ceiled amount of seconds to retry after
        """
        return self.retry_after.__int__() + 1
