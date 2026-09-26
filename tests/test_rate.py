import pytest

from uprate.rate import Minutes, Rate, RateGroup, Seconds


def test_rate_arithmetic_builds_expected_rates():
    assert 5 / Seconds == Rate(5, 1)
    assert 2 * Minutes == Rate(1, 120)
    assert Minutes / 2 == Rate(1, 30)
    assert Seconds + Minutes == Rate(1, 61)
    assert Seconds(3) == Rate(1, 3)


def test_rate_group_combines_rates_and_groups():
    group = 2 / Seconds | 3 / Minutes
    assert isinstance(group, RateGroup)
    assert group._data == [Rate(2, 1), Rate(3, 60)]

    combined = group | (4 / Seconds | 5 / Minutes)
    assert combined._data == [Rate(2, 1), Rate(3, 60), Rate(4, 1), Rate(5, 60)]


def test_unsupported_rate_operations_raise_type_error():
    with pytest.raises(TypeError):
        _ = Seconds | object()
    with pytest.raises(TypeError):
        _ = Seconds * object()
    with pytest.raises(TypeError):
        _ = Seconds / object()
    with pytest.raises(TypeError):
        _ = Seconds + object()


def test_adding_non_unit_rates_is_rejected():
    with pytest.raises(ValueError, match="uses other than one"):
        _ = (2 / Seconds) + Seconds
