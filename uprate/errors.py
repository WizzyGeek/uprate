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
    retry_after : float
        The amount of time to retry after in seconds.
    rate : Rate
        The rate that was violated
    """

    def __init__(self, retry_after: float, rate: Rate, *args):
        super().__init__(*args)
        self.retry_after = retry_after
        self.rate = rate
