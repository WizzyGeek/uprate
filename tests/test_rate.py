"""Unit tests for uprate.Rate and uprate.RateGroup (#18).

Covers the calculation behaviour and the defined *and* undefined
dunder operations:

Defined on Rate:
    __call__, __mul__, __rmul__, __truediv__, __rtruediv__, __add__,
    __radd__, __or__, __ror__, __eq__, __ne__, __hash__, __str__.

Defined on RateGroup:
    __init__, __or__, __ror__.

Every "undefined" operation that the library does not implement is asserted
to raise TypeError (the result of Python's dunder fallback when both the
forward and reverse operator return NotImplemented).
"""
from __future__ import annotations

import pytest as pt

from uprate.rate import (
    Days,
    Hours,
    Minutes,
    Months,
    Rate,
    RateGroup,
    Seconds,
    Weeks,
)


# ---------------------------------------------------------------------------
# Construction / attributes
# ---------------------------------------------------------------------------
def test_rate_stores_uses_and_period():
    r = Rate(5, 30.0)
    assert r.uses == 5
    assert r.period == 30.0


def test_rate_group_starts_empty():
    g = RateGroup()
    assert g._data == []


# ---------------------------------------------------------------------------
# Provided unit rates
# ---------------------------------------------------------------------------
def test_seconds_is_one_per_second():
    assert (Seconds.uses, Seconds.period) == (1, 1)


def test_unit_rates_are_consistent():
    assert (Minutes.uses, Minutes.period) == (1, 60)
    assert (Hours.uses, Hours.period) == (1, 3600)
    assert (Days.uses, Days.period) == (1, 86400)
    assert (Weeks.uses, Weeks.period) == (1, 604800)
    # Months is defined as 30 days in the library
    assert (Months.uses, Months.period) == (1, 2592000)


# ---------------------------------------------------------------------------
# __call__ : Rate(magnitude) scales the period
# ---------------------------------------------------------------------------
def test_call_scales_period():
    assert Seconds(3).period == 3
    assert Seconds(3).uses == 1


def test_call_scales_period_of_custom_rate():
    r = Rate(4, 10.0)
    assert (r(2).uses, r(2).period) == (4, 20.0)
    # the original is not mutated
    assert (r.uses, r.period) == (4, 10.0)


# ---------------------------------------------------------------------------
# __mul__ / __rmul__ : multiply the period
# ---------------------------------------------------------------------------
def test_mul_scales_period():
    assert (Seconds * 30).period == 30
    assert (Seconds * 30).uses == 1


def test_rmul_is_commutative_with_mul():
    a = Rate(2, 5.0)
    assert a * 4 == 4 * a
    assert (a * 4).period == 20.0


def test_mul_by_zero_gives_zero_period():
    assert (Rate(1, 10) * 0).period == 0


# ---------------------------------------------------------------------------
# __truediv__ : divide the period
# ---------------------------------------------------------------------------
def test_truediv_divides_period():
    assert (Rate(5, 2) / 4).period == 0.5
    assert (Rate(5, 2) / 4).uses == 5


def test_truediv_by_zero_raises():
    with pt.raises(ZeroDivisionError):
        Rate(1, 1) / 0.0


# ---------------------------------------------------------------------------
# __rtruediv__ : int / Rate -> uses=that int, period=rate.period
# ---------------------------------------------------------------------------
def test_rtruediv_by_int():
    r = 3 / Seconds
    assert isinstance(r, Rate)
    assert (r.uses, r.period) == (3, 1)


def test_rtruediv_uses_called_rates_period():
    # 1 / (Seconds(2)) -> Rate(1, 2)
    r = 1 / Seconds(2)
    assert (r.uses, r.period) == (1, 2)


# ---------------------------------------------------------------------------
# __add__ / __radd__ : only unitary (uses == 1) rates may be summed
# ---------------------------------------------------------------------------
def test_add_combines_periods_of_unitary_rates():
    r = Minutes + 30 * Seconds
    assert r.uses == 1
    assert r.period == 90.0


def test_add_with_seconds_and_minutes():
    assert (Minutes + Seconds).period == 61.0


def test_add_requires_unitary_uses():
    with pt.raises(ValueError, match="uses other than one"):
        Rate(5, 1) + Rate(1, 2)


def test_radd_is_commutative():
    assert Minutes + Seconds == Seconds + Minutes


def test_add_with_non_rate_raises():
    # Rate.__add__ returns NotImplemented for non-Rate, so Python raises
    with pt.raises(TypeError):
        Rate(1, 1) + 5


# ---------------------------------------------------------------------------
# __or__ / __ror__ : build a RateGroup
# ---------------------------------------------------------------------------
def test_rate_or_rate_builds_group():
    g = Rate(1, 1) | Rate(1, 2)
    assert isinstance(g, RateGroup)
    assert [ (r.uses, r.period) for r in g._data ] == [(1, 1), (1, 2)]


def test_chained_or_builds_group():
    g = Rate(1, 1) | Rate(1, 2) | Rate(1, 5)
    assert [ (r.uses, r.period) for r in g._data ] == [(1, 1), (1, 2), (1, 5)]


def test_rategroup_or_rate_appends_and_returns_self():
    g = RateGroup()
    g2 = g | Rate(1, 1)
    assert g2 is g
    assert [ (r.uses, r.period) for r in g._data ] == [(1, 1)]


def test_rategroup_or_rategroup_concatenates():
    a = Rate(1, 1) | Rate(1, 2)
    b = Rate(3, 4) | Rate(5, 6)
    combined = a | b
    assert [ (r.uses, r.period) for r in combined._data ] == [
        (1, 1), (1, 2), (3, 4), (5, 6),
    ]


def test_rate_or_rategroup_appends_rate():
    g = Rate(2, 2) | Rate(3, 3)
    result = Rate(1, 1) | g
    assert [ (r.uses, r.period) for r in result._data ] == [
        (2, 2), (3, 3), (1, 1),
    ]


def test_or_with_unsupported_type_returns_notimplemented_at_method_level():
    assert Rate(1, 1).__or__("x") is NotImplemented
    assert RateGroup().__or__("x") is NotImplemented


def test_or_with_unsupported_type_raises_typeerror_at_operator_level():
    with pt.raises(TypeError):
        Rate(1, 1) | "x"
    with pt.raises(TypeError):
        RateGroup() | "x"


# ---------------------------------------------------------------------------
# __eq__ / __ne__ / __hash__
# ---------------------------------------------------------------------------
def test_eq_same_uses_and_period():
    assert Rate(1, 1) == Rate(1, 1)


def test_eq_differs_when_uses_differ():
    assert Rate(1, 1) != Rate(2, 1)
    assert not (Rate(1, 1) == Rate(2, 1))


def test_eq_differs_when_period_differs():
    assert Rate(1, 1) != Rate(1, 2)


def test_eq_with_non_rate_is_not_equal():
    assert not (Rate(1, 1) == "x")


def test_ne_with_rate():
    assert Rate(1, 1) != Rate(1, 2)
    assert not (Rate(1, 1) != Rate(1, 1))


def test_hash_is_stable_for_equal_rates():
    assert hash(Rate(1, 1)) == hash(Rate(1, 1))


def test_rates_are_usable_in_set_and_dict():
    s = {Rate(1, 1), Rate(1, 1), Rate(2, 1)}
    assert len(s) == 2


# ---------------------------------------------------------------------------
# __str__
# ---------------------------------------------------------------------------
def test_str_formats_uses_over_period():
    assert str(Rate(1, 1)) == "1/1"
    assert str(Rate(5, 30)) == "5/30"


# ---------------------------------------------------------------------------
# undefined operations -> TypeError (no dunder implemented)
# ---------------------------------------------------------------------------
def test_sub_not_supported():
    a = Rate(1, 1)
    with pt.raises(TypeError):
        a - a
    with pt.raises(TypeError):
        5 - a


def test_mul_rate_by_rate_not_supported():
    with pt.raises(TypeError):
        Rate(1, 1) * Rate(1, 1)


def test_pow_not_supported():
    with pt.raises(TypeError):
        Rate(1, 1) ** 2


def test_xor_not_supported():
    with pt.raises(TypeError):
        Rate(1, 1) ^ 2


def test_comparisons_not_supported():
    a = Rate(1, 1)
    with pt.raises(TypeError):
        a > a
    with pt.raises(TypeError):
        a < a


def test_len_not_supported():
    with pt.raises(TypeError):
        len(Rate(1, 1))


def test_group_sub_not_supported():
    with pt.raises(TypeError):
        RateGroup() - Rate(1, 1)


# ---------------------------------------------------------------------------
# integration-style expression from the module docstring
# ---------------------------------------------------------------------------
def test_docstring_style_expression():
    # 30 uses per 2 min 30 sec, expressed with the operators
    rate = 30 / (2 * Minutes + 30 * Seconds)
    assert isinstance(rate, Rate)
    assert rate.uses == 30
    assert rate.period == 150.0


def test_two_tier_rate_group():
    group = 2 / Seconds(2) | 30 / (2 * Minutes + 30 * Seconds)
    assert isinstance(group, RateGroup)
    assert len(group._data) == 2
    assert group._data[0] == Rate(2, 2)
    assert group._data[1] == Rate(30, 150.0)
