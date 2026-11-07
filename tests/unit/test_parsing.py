from decimal import Decimal

import pytest

from airbnb_pipeline.parsing import PriceParseError, parse_price


@pytest.mark.parametrize(
    ("raw", "amount", "currency"),
    [
        ("$364.75", Decimal("364.75"), "$"),
        ("$1,141.33", Decimal("1141.33"), "$"),
        ("$1,234,567.89", Decimal("1234567.89"), "$"),
        ("€1.141,33", Decimal("1141.33"), "€"),
        ("EUR 1.234,56", Decimal("1234.56"), "EUR"),
        ("1 141,33", Decimal("1141.33"), None),
        ("1'141.33", Decimal("1141.33"), None),
        ("1141", Decimal("1141"), None),
        ("1141.5", Decimal("1141.5"), None),
        ("1141,5", Decimal("1141.5"), None),
        ("-$5.00", Decimal("-5.00"), "$"),
        ("$ 364.75", Decimal("364.75"), "$"),
    ],
)
def test_parse_price_accepts_supported_formats(raw, amount, currency):
    result = parse_price(raw)

    assert result is not None
    assert result.raw == raw
    assert result.amount == amount
    assert result.currency == currency


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_price_returns_none_for_missing(raw):
    assert parse_price(raw) is None


@pytest.mark.parametrize(
    "raw",
    [
        "$1,234",
        "$1.234",
        "$1,23,456.78",
        "$1,234.56.78",
        "abc",
        "$",
        "$1,234.",
        "$1,,234",
    ],
)
def test_parse_price_rejects_invalid_or_ambiguous(raw):
    with pytest.raises(PriceParseError):
        parse_price(raw)
