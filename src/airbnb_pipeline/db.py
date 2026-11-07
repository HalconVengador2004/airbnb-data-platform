from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as Connection

from airbnb_pipeline import config


def get_connection() -> Connection:
    return psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        dbname=config.POSTGRES_DB,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        connect_timeout=10,
    )


def apply_sql_file(conn: Connection, path: Path) -> None:
    sql_text = path.read_text(encoding="utf-8")
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)
