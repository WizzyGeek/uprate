from __future__ import annotations

from inspect import isawaitable
from typing import Awaitable, Callable, TypeVar, Union
from time import time_ns, monotonic_ns

R = TypeVar("R")

__all__ = (
    "maybe_awaitable",
    "monotonic_to_unix",
)

MAX_SAMPLE_DURATION_NS: int = 2500
GLOBAL_UNIX_MONO_DELTA_NS: int = 0
MAX_UNIX_MONO_DRIFT_NS: int = 50000
Clock = Callable[[], int]


async def maybe_awaitable(ret: Union[R, Awaitable[R]]) -> R:
    if isawaitable(ret):
        return await ret
    else:
        return ret


def monotonic_to_unix(time_sec: float) -> float:
    """Converts a monotonic timestamp in seconds to unix timestamp in seconds"""
    return time_sec + get_unix_monotonic_delta() / 1e9


def monotonic_to_unix_ns(time_nano: int) -> int:
    """Converts a monotonic timestamp in nanoseconds to unix timestamp in nanoseconds"""
    return time_nano + get_unix_monotonic_delta()


def get_unix_monotonic_delta() -> int:
    global GLOBAL_UNIX_MONO_DELTA_NS
    m1 = monotonic_ns()
    u1 = time_ns()
    now_delta = u1 - m1

    if abs(now_delta - GLOBAL_UNIX_MONO_DELTA_NS) >= MAX_UNIX_MONO_DRIFT_NS:
        delta, cacheable = _find_clock_delta(time_ns, monotonic_ns)
        if cacheable:
            GLOBAL_UNIX_MONO_DELTA_NS = delta
        return delta

    return GLOBAL_UNIX_MONO_DELTA_NS


def _find_clock_delta(
    clocku: Clock, clockm: Clock, nsamples: int = 5
) -> tuple[int, bool]:
    """Finds the delta between two clocks

    Working
    -------
    Uses a 7 point sampling technique

        m1 -> u1 -> m2 -> u2 -> m3 -> u3 -> m4

    Then we derive 10 independent estimators from this chain:

    Archetype 1: Localized 3 point Sandwiches
    - delta_1 = u1 - (m1 + m2) / 2
    - delta_2 = u2 - (m2 + m3) / 2
    - delta_3 = u3 - (m3 + m4) / 2
    - delta_4 = (u1 + u2) / 2 - m2
    - delta_5 = (u2 + u3) / 2 - m3

    Archetype 2: Symmetric Long-Spans
    - delta_6 = (u1 + u3) / 2 - (m2 + m3) / 2
    - delta_7 = (u1 + u3) / 2 - (m1 + m4) / 2
    - delta_8 = (u1 + u2 + u3) / 3 - (m1 + m4) / 2

    Archetype 3: Fractionally Weighted Asymmetric Engines
    - delta_9  = (u1 + 3 * u2 + 2 * u3) / 6 - (m1 + m3 + m4) / 3
    - delta_10 = (2 * u1 + 3 * u2 + u3) / 6 - (m1 + m2 + m4) / 3

    Averaging all 10 estimators forces unaligned phase errors to completely cancel out:

    Global Delta = (20 * (u1 + u2 + u3) - (13 * m1 + 17 * m2 + 17 * m3 + 13 * m4)) / 60

    This makes ONE delta sample, by default nsamples specifies 5 samples
    50% of the samples are trimmed, and the mean is returned.

    If enough samples aren't collected then a basic fallback 3 point method returns the first sample

    Parameters
    ----------
    clocku : Callable[[], int]
        A high precision clock returning integers
    clockm : Callable[[], int]
        A high precision clock returning integers
    nsamples : int, optional
        How many samples to collect, by default 5

    Returns
    -------
    tuple[int, bool]
        [0] - int - The delta between clocku and clockm, specifically the (clocku - clockm)
        [1] - bool - Whether you should cache this value or not. True if high confidence.
    """
    samples: list[int] = []
    attempts = nsamples * 5

    while len(samples) < nsamples and attempts > 0:
        # Keep it clean
        m1 = clockm()
        u1 = clocku()
        m2 = clockm()
        u2 = clocku()
        m3 = clockm()
        u3 = clocku()
        m4 = clockm()

        attempts -= 1
        if (m4 - m1) > MAX_SAMPLE_DURATION_NS:
            continue

        delta = (20 * (u1 + u2 + u3) - 13 * (m1 + m4) - 17 * (m3 + m2)) // 60
        samples.append(delta)

    if not samples:
        m1 = clockm()
        u1 = clocku()
        m2 = clockm()
        return u1 - (m1 + m2) // 2, False

    samples.sort()
    if len(samples) >= 4:
        ndrop = len(samples) // 4
        samples = samples[ndrop:-ndrop]
    return sum(samples) // len(samples), True


# Formula 1 (Rigid Optimum): (3*(U1 + U3) + 2*U2 - (M1 + 3*M2 + 3*M3 + M4)) // 8
# Discarded because it assumes a perfectly rigid textbook execution grid, causing it to fail under real-world asymmetric system call latencies.

# Formula 2 (Combinatorial Mesh): (4*(U1 + U3) + 3*U2 - (M1 + 4*M2 + 4*M3 + M4)) // 11
# Discarded because it over-filters the outer boundaries at the expense of capturing the localized, uniform distribution of the internal Unix timeline.

# Formula 3 (Asymmetric Phase-Compensated): (5*(U1 + U3) + 6*U2 - (M1 + 5*M2 + 5*M3 + M4)) // 16
# Discarded because its extreme prioritization of the central Unix anchor leaves it mathematically skewed if a micro-stall occurs right at the middle of the execution loop.
