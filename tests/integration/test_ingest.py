import csv
import os

import pytest

from airbnb_pipeline import config
from airbnb_pipeline.datasets import LISTINGS, LISTINGS_COLUMNS
from airbnb_pipeline.db import apply_sql_file, get_connection
from airbnb_pipeline.ingestion.loader import load_dataset

pytestmark = pytest.mark.integration


@pytest.fixture
def connection():
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to run integration tests")

    conn = get_connection()
    apply_sql_file(conn, config.SQL_DIR / "001_init.sql")
    yield conn

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM raw.listings WHERE _city = %s",
            ("integration_test",),
        )
        cur.execute(
            "DELETE FROM ingestion.file_manifest WHERE city = %s",
            ("integration_test",),
        )
    conn.commit()
    conn.close()


def write_listing(path):
    row = {column: "" for column in LISTINGS_COLUMNS}
    row.update(
        {
            "id": "1",
            "scrape_id": "99999999999999",
            "latitude": "40.4168",
            "longitude": "-3.7038",
            "property_type": "Apartment",
            "room_type": "Entire home/apt",
            "accommodates": "2",
            "neighbourhood_cleansed": "Centro",
            "neighbourhood_group_cleansed": "Centro",
            "price": "$100.00",
        }
    )

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LISTINGS_COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def test_load_is_idempotent(connection, tmp_path):
    path = tmp_path / "listings_integration_test.csv"
    write_listing(path)

    first = load_dataset(connection, LISTINGS, "integration_test", path)
    second = load_dataset(connection, LISTINGS, "integration_test", path)

    assert first.status == "loaded"
    assert first.row_count == 1
    assert second.status == "skipped"

    with connection.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM raw.listings WHERE _city = %s",
            ("integration_test",),
        )
        assert cur.fetchone()[0] == 1
