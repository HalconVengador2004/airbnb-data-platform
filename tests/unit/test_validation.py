import csv

import pytest

from airbnb_pipeline.datasets import DatasetSpec
from airbnb_pipeline.validation.listings import ValidationError, validate_listings

COLUMNS = (
    "id",
    "scrape_id",
    "price",
    "latitude",
    "longitude",
    "property_type",
    "room_type",
    "accommodates",
    "neighbourhood_cleansed",
    "neighbourhood_group_cleansed",
)

SPEC = DatasetSpec(
    name="listings",
    table="raw.listings",
    key_columns=("scrape_id", "id"),
    required_columns=tuple(column for column in COLUMNS if column != "price"),
    price_column="price",
)


def valid_row(**overrides):
    row = {
        "id": "1",
        "scrape_id": "123",
        "price": "$100.00",
        "latitude": "40.4168",
        "longitude": "-3.7038",
        "property_type": "Apartment",
        "room_type": "Entire home/apt",
        "accommodates": "2",
        "neighbourhood_cleansed": "Centro",
        "neighbourhood_group_cleansed": "Centro",
    }
    row.update(overrides)
    return row


def write_csv(path, rows, columns=COLUMNS):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def test_valid_file(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row()])

    report = validate_listings(path, SPEC, COLUMNS)

    assert report.ok
    assert report.row_count == 1
    assert report.scrape_ids == ("123",)
    assert report.price_parsed == 1
    assert report.price_null == 0
    assert report.price_failed == 0


def test_empty_price_is_allowed(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(price="")])

    report = validate_listings(path, SPEC, COLUMNS)

    assert report.ok
    assert report.price_null == 1


def test_duplicate_key_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(), valid_row()])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert exc_info.value.report.duplicate_keys == 1


def test_multiple_scrape_ids_are_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(), valid_row(id="2", scrape_id="456")])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "expected exactly one scrape_id" in " ".join(
        exc_info.value.report.errors
    )


def test_unparseable_price_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(price="$1,234")])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert exc_info.value.report.price_failed == 1


def test_negative_price_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(price="-$5.00")])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "negative" in " ".join(exc_info.value.report.errors)


def test_missing_column_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    columns = tuple(column for column in COLUMNS if column != "room_type")
    write_csv(path, [valid_row()], columns)

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "missing columns" in " ".join(exc_info.value.report.errors)


def test_extra_column_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    columns = COLUMNS + ("extra",)
    write_csv(path, [valid_row(extra="value")], columns)

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "unexpected columns" in " ".join(exc_info.value.report.errors)


def test_out_of_range_coordinate_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(latitude="100")])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "out of range" in " ".join(exc_info.value.report.errors)


def test_invalid_accommodates_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [valid_row(accommodates="two")])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "not an integer" in " ".join(exc_info.value.report.errors)


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "listings.csv"
    write_csv(path, [])

    with pytest.raises(ValidationError) as exc_info:
        validate_listings(path, SPEC, COLUMNS)

    assert "no data rows" in " ".join(exc_info.value.report.errors)
