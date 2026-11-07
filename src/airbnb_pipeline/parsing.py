import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


class PriceParseError(ValueError):
    pass


@dataclass(frozen=True)
class Price:
    raw: str
    amount: Decimal
    currency: Optional[str]


CURRENCY_SYMBOLS = {"$", "€", "£", "¥"}
CURRENCY_CODE_PATTERN = re.compile(r"^([A-Za-z]{3})\s*")
SPACE_PATTERN = re.compile(r"[\s\u00a0\u202f]")
NUMERIC_PATTERN = re.compile(r"^[0-9.,']+$")


def parse_price(value: Optional[str]) -> Optional[Price]:
    if value is None:
        return None

    raw = value
    text = value.strip()
    if not text:
        return None

    sign = ""
    if text[0] in "+-":
        sign = text[0]
        text = text[1:].strip()

    currency = None
    if text and text[0] in CURRENCY_SYMBOLS:
        currency = text[0]
        text = text[1:].strip()
    else:
        match = CURRENCY_CODE_PATTERN.match(text)
        if match:
            currency = match.group(1).upper()
            text = text[match.end():]

    text = SPACE_PATTERN.sub("", sign + text)
    if not text:
        raise PriceParseError(f"price has no numeric value: {raw!r}")

    return Price(raw=raw, amount=_parse_amount(text, raw), currency=currency)


def _parse_amount(text: str, raw: str) -> Decimal:
    sign = 1
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1
        text = text[1:]

    if not text:
        raise PriceParseError(f"price has no numeric value: {raw!r}")

    if not NUMERIC_PATTERN.match(text):
        raise PriceParseError(f"price contains unsupported characters: {raw!r}")

    text = text.replace("'", "")

    if not text:
        raise PriceParseError(f"price has no numeric value: {raw!r}")

    if "." in text and "," in text:
        decimal_separator = "." if text.rfind(".") > text.rfind(",") else ","
        thousands_separator = "," if decimal_separator == "." else "."
        integer_part, decimal_part = text.rsplit(decimal_separator, 1)
        _validate_integer_part(integer_part, thousands_separator, raw)
        _validate_decimal_part(decimal_part, raw)
    elif "." in text or "," in text:
        separator = "." if "." in text else ","
        occurrences = text.count(separator)
        if occurrences > 1:
            integer_part = text
            decimal_part = ""
            thousands_separator = separator
            _validate_integer_part(integer_part, thousands_separator, raw)
        else:
            integer_part, decimal_part = text.split(separator)
            if len(decimal_part) == 3:
                raise PriceParseError(f"ambiguous separator in price: {raw!r}")
            if not decimal_part:
                raise PriceParseError(f"missing digits after separator in price: {raw!r}")
            thousands_separator = None
            _validate_integer_part(integer_part, thousands_separator, raw)
            _validate_decimal_part(decimal_part, raw)
    else:
        integer_part = text
        decimal_part = ""
        thousands_separator = None
        _validate_integer_part(integer_part, thousands_separator, raw)

    integer_digits = (
        integer_part.replace(thousands_separator, "")
        if thousands_separator
        else integer_part
    )
    normalized = f"{integer_digits}.{decimal_part or '0'}"

    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise PriceParseError(f"price is not a valid decimal: {raw!r}") from exc

    return amount * sign


def _validate_integer_part(
    part: str,
    thousands_separator: Optional[str],
    raw: str,
) -> None:
    if not part:
        raise PriceParseError(f"price is missing an integer part: {raw!r}")

    if thousands_separator is None or thousands_separator not in part:
        if not part.isdigit():
            raise PriceParseError(f"price has an invalid integer part: {raw!r}")
        return

    groups = part.split(thousands_separator)
    if not groups[0].isdigit() or not 1 <= len(groups[0]) <= 3:
        raise PriceParseError(f"price has invalid thousands grouping: {raw!r}")

    for group in groups[1:]:
        if len(group) != 3 or not group.isdigit():
            raise PriceParseError(f"price has invalid thousands grouping: {raw!r}")


def _validate_decimal_part(part: str, raw: str) -> None:
    if not part or not part.isdigit():
        raise PriceParseError(f"price has an invalid decimal part: {raw!r}")
