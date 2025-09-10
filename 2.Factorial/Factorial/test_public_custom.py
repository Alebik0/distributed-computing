import pytest

from factorial import factorial


def test_factorial_zero():
    assert factorial(0) == 1


def test_factorial_positive_number():
    assert factorial(4) == 24


def test_factorial_another_positive_number():
    assert factorial(5) == 120


def test_factorial_negative_number():
    with pytest.raises(RecursionError):
        factorial(-3)
