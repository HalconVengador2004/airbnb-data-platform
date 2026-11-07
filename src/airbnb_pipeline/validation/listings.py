import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

from airbnb_pipeline.datasets import LISTINGS_COLUMNS, DatasetSpec
from airbnb_pipeline.parsing import PriceParseError, parse_price

MAX_ERRORS = 50


@dataclass(frozen=True)
class ValidationReport:
    path: Path
    row_count: int
    scrape_ids: tuple[str, ...]
    price_parsed: int
    price_null: int
    price_failed: int
    duplicate_keys: int
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    error_count: int

    @property
    def ok(self) -> bool:
        return self.error_count == 0


class ValidationError(Exception):
    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__(
            f"validation failed for {report.path}: {report.error_count} error(s)"
        )


class _ErrorCollector:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.count = 0

    def add(self, message: str) -> None:
        self.count += 1
        if len(self.errors) < MAX_ERRORS:
            self.errors.append(message)


def validate_listings(
    path: Path,
    spec: DatasetSpec,
    expected_columns: Sequence[str] = LISTINGS_COLUMNS,
) -> ValidationReport:
    if not path.is_file():
        raise ValidationError(_empty_report(path, (f"file not found: {path}",)))

    errors = _ErrorCollector()
    warnings: list[str] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames

        if header is None:
            raise ValidationError(_empty_report(path, ("file has no header",)))

        header_errors = _validate_header(header, expected_columns)
        if header_errors:
            raise ValidationError(_empty_report(path, tuple(header_errors)))

        seen: set[tuple[str, str]] = set()
        scrape_ids: set[str] = set()
        row_count = 0
        price_parsed = 0
        price_null = 0
        price_failed = 0
        duplicate_keys = 0

        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            if None in row:
                errors.add(
                    f"line {line_number}: row has more fields than the header"
                )
            row_id = _value(row, "id")
            scrape_id = _value(row, "scrape_id")

            if scrape_id:
                scrape_ids.add(scrape_id)

            if row_id and scrape_id:
                key = (scrape_id, row_id)
                if key in seen:
                    duplicate_keys += 1
                    errors.add(f"line {line_number}: duplicate key {key}")
                else:
                    seen.add(key)

            for column in spec.required_columns:
                if not _value(row, column):
                    errors.add(
                        f"line {line_number}: required column {column} is empty"
                    )

            raw_price = row.get(spec.price_column) if spec.price_column else None
            if raw_price is None or not raw_price.strip():
                price_null += 1
            else:
                try:
                    price = parse_price(raw_price)
                except PriceParseError as exc:
                    price_failed += 1
                    errors.add(f"line {line_number}: {exc}")
                else:
                    if price is None:
                        price_null += 1
                    elif price.amount < 0:
                        errors.add(
                            f"line {line_number}: price is negative: {raw_price!r}"
                        )
                    else:
                        price_parsed += 1

            _validate_coordinates(row, line_number, errors)
            _validate_integer(row, "accommodates", line_number, errors)

    if row_count == 0:
        errors.add("file has no data rows")

    if len(scrape_ids) != 1:
        errors.add(
            f"expected exactly one scrape_id, found {len(scrape_ids)}: "
            f"{sorted(scrape_ids)[:5]}"
        )

    if price_failed:
        errors.add(f"{price_failed} price value(s) failed to parse")

    report = ValidationReport(
        path=path,
        row_count=row_count,
        scrape_ids=tuple(sorted(scrape_ids)),
        price_parsed=price_parsed,
        price_null=price_null,
        price_failed=price_failed,
        duplicate_keys=duplicate_keys,
        warnings=tuple(warnings),
        errors=tuple(errors.errors),
        error_count=errors.count,
    )

    if not report.ok:
        raise ValidationError(report)

    return report


def _empty_report(path: Path, errors: tuple[str, ...]) -> ValidationReport:
    return ValidationReport(
        path=path,
        row_count=0,
        scrape_ids=(),
        price_parsed=0,
        price_null=0,
        price_failed=0,
        duplicate_keys=0,
        warnings=(),
        errors=errors,
        error_count=len(errors),
    )


def _validate_header(
    header: Sequence[str],
    expected_columns: Sequence[str],
) -> list[str]:
    errors: list[str] = []

    if len(header) != len(set(header)):
        errors.append("header contains duplicate column names")

    expected_set = set(expected_columns)
    header_set = set(header)
    missing = sorted(expected_set - header_set)
    extra = sorted(header_set - expected_set)

    if missing:
        errors.append(f"header is missing columns: {missing}")
    if extra:
        errors.append(f"header has unexpected columns: {extra}")

    return errors


def _value(row: dict[str, str | None], column: str) -> str:
    value = row.get(column)
    return value.strip() if isinstance(value, str) else ""


def _validate_coordinates(
    row: dict[str, str | None],
    line_number: int,
    errors: _ErrorCollector,
) -> None:
    for column, lower, upper in (
        ("latitude", Decimal("-90"), Decimal("90")),
        ("longitude", Decimal("-180"), Decimal("180")),
    ):
        value = _value(row, column)
        if not value:
            continue

        try:
            number = Decimal(value)
        except InvalidOperation:
            errors.add(f"line {line_number}: {column} is not numeric: {value!r}")
            continue

        if not lower <= number <= upper:
            errors.add(f"line {line_number}: {column} is out of range: {value!r}")


def _validate_integer(
    row: dict[str, str | None],
    column: str,
    line_number: int,
    errors: _ErrorCollector,
) -> None:
    value = _value(row, column)
    if not value:
        return

    try:
        int(value)
    except ValueError:
        errors.add(f"line {line_number}: {column} is not an integer: {value!r}")
