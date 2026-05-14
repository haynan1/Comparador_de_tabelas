from decimal import Decimal

from app.services.normalizer import parse_money


def test_parse_money_brazilian_decimal():
    assert parse_money("194,46") == Decimal("194.46")


def test_parse_money_with_currency_and_thousands():
    assert parse_money("R$ 1.042,88") == Decimal("1042.88")


def test_parse_money_dot_decimal():
    assert parse_money("1042.88") == Decimal("1042.88")


def test_parse_money_invalid():
    assert parse_money("total") is None
