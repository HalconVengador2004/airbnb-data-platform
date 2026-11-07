import re
from pathlib import Path

from airbnb_pipeline.datasets import LISTINGS_COLUMNS

SQL_PATH = Path(__file__).resolve().parents[2] / "sql" / "001_init.sql"


def test_listings_table_matches_observed_columns():
    sql = SQL_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS raw\.listings \((.*?)\);",
        sql,
        re.S,
    )

    assert match is not None

    body = match.group(1)
    columns = re.findall(
        r"^\s{4}([a-z][a-z0-9_]*)\s+TEXT,?\s*$",
        body,
        re.M,
    )

    assert tuple(columns) == LISTINGS_COLUMNS
    assert len(columns) == 90
