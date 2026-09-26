from math import sqrt

import pytest as pt
from unittest.mock import AsyncMock
from time import monotonic, monotonic_ns, time_ns
from logging import info

from uprate._utils import (
    maybe_awaitable,
    monotonic_to_unix,
    _find_clock_delta,
    monotonic_to_unix_ns,
)
import uprate._utils as utils


MAX_STDDEV_NS = 1000


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
    for _ in range(1000):
        est = _find_clock_delta(time_ns, monotonic_ns)[0]
        samples.append(est)

    samples.sort()

    n_clean = len(samples)
    mo = sum(samples) // n_clean
    vo = sum((x - mo) ** 2 for x in samples) / (n_clean - 1)
    stddev = sqrt(vo)

    score = ((MAX_STDDEV_NS - stddev) / MAX_STDDEV_NS) ** 4

    assert score > 0, (
        f"_find_clock_delta: stddev too high"
        f"score: {score:.3f} | stddev: {stddev} ns | var: {vo} ns^2 | mean: {mo}"
    )

    info(
        f"_find_clock_delta: score: {score:.3f} | stddev: {stddev} ns | var: {vo} ns^2 | mean: {mo}"
    )
    info(f"_find_clock_delta: spread: {max(samples) - min(samples)} ns")


def test_monotonic_unix_drift(monkeypatch: pt.MonkeyPatch):
    with monkeypatch.context() as m:
        DELTA = utils.get_unix_monotonic_delta()
        # Mocking monotonic is bad idea
        # m.setattr("uprate._utils.monotonic_ns", lambda: time_ns() - DELTA - utils.MAX_UNIX_MONO_DRIFT_NS - MAX_STDDEV_NS)
        m.setattr(
            "uprate._utils.time_ns",
            lambda: (
                monotonic_ns() + DELTA + utils.MAX_UNIX_MONO_DRIFT_NS + MAX_STDDEV_NS
            ),
        )
        DELTA2 = utils.get_unix_monotonic_delta()

        DD = DELTA2 - DELTA
        assert DD != 0, "No drift correction happened on monotonic mocking"
        assert abs(DD - utils.MAX_UNIX_MONO_DRIFT_NS) <= 3 * MAX_STDDEV_NS, (
            f"Observed a incorrect drift correction | absolute error: {abs(DD - utils.MAX_UNIX_MONO_DRIFT_NS)} ns "
            f"| permissible absolute error: {3 * MAX_STDDEV_NS} ns"
        )
        info(f"The drift captured is {DD} | {DELTA} --drifted--> {DELTA2}")


def test_monotonic_unix_ns_conversion():
    DELAY = 20_000_000_000  # 20 secs
    m1 = monotonic_ns()

    while True:
        u1 = monotonic_to_unix_ns(m1)
        ODELTA = utils.GLOBAL_UNIX_MONO_DELTA_NS
        # go twenty seconds ahead
        m2 = m1 + DELAY
        u2 = monotonic_to_unix_ns(m2)
        SDELTA = utils.GLOBAL_UNIX_MONO_DELTA_NS

        if ODELTA != SDELTA:  # usually very unlikely
            if (monotonic_ns() - m1) >= DELAY:
                # Please report if this assertion is ever reached
                assert False, "Excessively frequent DELTA updation"
            continue

        u_delay = u2 - u1
        assert u_delay == DELAY, f"Same delta conversion inaccuracy"
        assert isinstance(u2, int) and isinstance(u1, int), (
            f"Conversion yielded incorrect types"
        )
        return


def test_monotonic_unix_conversion():
    DELAY = 20
    start = monotonic_ns()
    m1 = monotonic()

    while True:
        u1 = monotonic_to_unix(m1)
        ODELTA = utils.GLOBAL_UNIX_MONO_DELTA_NS
        # go twenty seconds ahead
        m2 = m1 + DELAY
        u2 = monotonic_to_unix(m2)
        SDELTA = utils.GLOBAL_UNIX_MONO_DELTA_NS

        if ODELTA != SDELTA:  # usually very unlikely
            if (monotonic_ns() - start) >= DELAY * 1_000_000_000:
                # Please report if this assertion is ever reached
                assert False, "Excessively frequent DELTA updation"
            continue

        u_delay = u2 - u1
        assert pt.approx(u_delay, abs=1e-10) == DELAY, (
            f"Same delta conversion inaccuracy"
        )
        assert isinstance(u2, float) and isinstance(u1, float), (
            f"Conversion yielded incorrect types"
        )
        return


def test_monotonic_unix_ns_conversion_calculation(monkeypatch: pt.MonkeyPatch):
    TARGET_DELTA_NS = 2_000_000_000000_001_000
    MONO_UPTIME_NS = 231_000_000_000
    NS_TO_SEC = 1e-9
    SEC_TO_NS = 1e9
    FLOAT_TOLERANCE = 1e-6
    TARGET_DELTA_SEC = pt.approx(TARGET_DELTA_NS * SEC_TO_NS, abs=FLOAT_TOLERANCE)
    with monkeypatch.context() as m:
        # Assume our clocks are frozen in time
        # our methods should work even better in this case
        m.setattr("uprate._utils.time_ns", lambda: MONO_UPTIME_NS + TARGET_DELTA_NS)
        m.setattr("uprate._utils.monotonic_ns", lambda: MONO_UPTIME_NS)

        m1 = MONO_UPTIME_NS * 2
        u1 = monotonic_to_unix_ns(m1)

        USED_DELTA = u1 - m1
        assert USED_DELTA == TARGET_DELTA_NS, "Conversion is errorneous"

        m1 = MONO_UPTIME_NS * 100000 + 987654321
        u1 = monotonic_to_unix_ns(m1)
        USED_DELTA = u1 - m1
        assert USED_DELTA == TARGET_DELTA_NS, (
            "Conversion violates time translational symmetry"
        )


def test_monotonic_unix_conversion_calculation(monkeypatch: pt.MonkeyPatch):
    TARGET_DELTA_NS = 2_000_000_000000_001_000
    MONO_UPTIME_NS = 231_000_000_000
    NS_TO_SEC = 1e-9
    FLOAT_TOLERANCE = 1e-6
    TARGET_DELTA_SEC = pt.approx(TARGET_DELTA_NS * NS_TO_SEC, abs=FLOAT_TOLERANCE)
    with monkeypatch.context() as m:
        m.setattr("uprate._utils.time_ns", lambda: MONO_UPTIME_NS + TARGET_DELTA_NS)
        m.setattr("uprate._utils.monotonic_ns", lambda: MONO_UPTIME_NS)

        m1 = MONO_UPTIME_NS * 2 * NS_TO_SEC
        u1 = monotonic_to_unix(m1)
        USED_DELTA = u1 - m1
        assert USED_DELTA == TARGET_DELTA_SEC, "Conversion is errorneous"

        m1 = (MONO_UPTIME_NS * 100000 + 987654321) * NS_TO_SEC
        u1 = monotonic_to_unix(m1)
        USED_DELTA = u1 - m1
        assert USED_DELTA == TARGET_DELTA_SEC, (
            "Conversion violates time translational symmetry"
        )
