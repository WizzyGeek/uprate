from math import sqrt

import pytest as pt
from unittest.mock import AsyncMock
from time import monotonic_ns, time_ns
from logging import info

from uprate._utils import maybe_awaitable, monotonic_to_unix, _find_clock_delta


@pt.fixture()
async def amock():
    return AsyncMock()

@pt.fixture()
async def sent():
    return object()


async def test_maybe_awaitable_awaitable(amock: AsyncMock, sent: object):
    amock.return_value = sent
    assert await maybe_awaitable(amock()) is sent


async def test_maybe_awaitable_sync(sent: object):
    assert await maybe_awaitable(sent) is sent

def test__find_clock_delta_error_dist():
    # We dont care about the correct answer (NTP etc.)
    # we care about a consistent answer!
    samples = []
    for _ in range(100):
        est = _find_clock_delta(time_ns, monotonic_ns, nsamples=1)[0]
        samples.append(est)

    samples.sort()

    n_clean = len(samples)
    mo = sum(samples) / n_clean
    vo = sum((x - mo) ** 2 for x in samples) / (n_clean - 1)
    stddev = sqrt(vo)

    MAX_STDDEV_NS = 1000
    score = ((MAX_STDDEV_NS - stddev) / MAX_STDDEV_NS) ** 4

    assert score > 0, (
        f"_find_clock_delta: stddev too high"
        f"score: {score:.3f} | stddev: {stddev} ns | var: {vo} ns^2"
    )

    info(f"_find_clock_delta: score: {score:.3f} | stddev: {stddev} ns | var: {vo} ns^2")
