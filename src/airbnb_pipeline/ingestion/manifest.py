from dataclasses import dataclass
from datetime import datetime

from psycopg2.extensions import connection as Connection
from psycopg2.extras import RealDictCursor


@dataclass(frozen=True)
class ManifestEntry:
    dataset: str
    city: str
    scrape_id: str
    source_file: str
    file_hash: str
    row_count: int
    status: str
    error_message: str | None
    loaded_at: datetime


def get_entry_by_hash(
    conn: Connection,
    dataset: str,
    city: str,
    file_hash: str,
) -> ManifestEntry | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT dataset, city, scrape_id, source_file, file_hash, row_count,
                   status, error_message, loaded_at
            FROM ingestion.file_manifest
            WHERE dataset = %s
              AND city = %s
              AND file_hash = %s
              AND status = 'loaded'
            ORDER BY loaded_at DESC
            LIMIT 1
            """,
            (dataset, city, file_hash),
        )
        row = cur.fetchone()

    return ManifestEntry(**row) if row else None


def upsert_loaded(
    conn: Connection,
    dataset: str,
    city: str,
    scrape_id: str,
    source_file: str,
    file_hash: str,
    row_count: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion.file_manifest
                (dataset, city, scrape_id, source_file, file_hash, row_count,
                 status, error_message, loaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'loaded', NULL, now())
            ON CONFLICT (dataset, city, scrape_id) DO UPDATE SET
                source_file = EXCLUDED.source_file,
                file_hash = EXCLUDED.file_hash,
                row_count = EXCLUDED.row_count,
                status = 'loaded',
                error_message = NULL,
                loaded_at = now()
            """,
            (dataset, city, scrape_id, source_file, file_hash, row_count),
        )
