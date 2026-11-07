import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from psycopg2 import sql
from psycopg2.extensions import connection as Connection

from airbnb_pipeline.datasets import DatasetSpec
from airbnb_pipeline.ingestion.manifest import get_entry_by_hash, upsert_loaded
from airbnb_pipeline.validation import validate_dataset


@dataclass(frozen=True)
class LoadResult:
    dataset: str
    city: str
    scrape_id: str
    file_hash: str
    row_count: int
    status: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset(
    conn: Connection,
    spec: DatasetSpec,
    city: str,
    path: Path,
) -> LoadResult:
    file_hash = sha256_file(path)

    existing = get_entry_by_hash(conn, spec.name, city, file_hash)
    conn.commit()
    if existing is not None:
        return LoadResult(
            dataset=spec.name,
            city=city,
            scrape_id=existing.scrape_id,
            file_hash=file_hash,
            row_count=existing.row_count,
            status="skipped",
        )

    report = validate_dataset(path, spec)
    scrape_id = report.scrape_ids[0]

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)",
                (f"{spec.name}:{city}:{scrape_id}",),
            )

        existing = get_entry_by_hash(conn, spec.name, city, file_hash)
        if existing is not None:
            return LoadResult(
                dataset=spec.name,
                city=city,
                scrape_id=existing.scrape_id,
                file_hash=file_hash,
                row_count=existing.row_count,
                status="skipped",
            )

        with path.open("r", encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
            handle.seek(0)

            temp_table = sql.Identifier(f"_load_{spec.name}")
            target_table = sql.Identifier(*spec.table.split("."))
            column_definitions = sql.SQL(", ").join(
                sql.SQL("{} TEXT").format(sql.Identifier(column))
                for column in header
            )

            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(
                        temp_table,
                        column_definitions,
                    )
                )

                copy_statement = sql.SQL(
                    "COPY {} FROM STDIN WITH "
                    "(FORMAT csv, HEADER true, ENCODING 'UTF8')"
                ).format(temp_table)
                cur.copy_expert(copy_statement.as_string(conn), handle)

                cur.execute(
                    sql.SQL(
                        "DELETE FROM {} WHERE _city = %s AND scrape_id = %s"
                    ).format(target_table),
                    (city, scrape_id),
                )
                deleted_rows = cur.rowcount

                insert_columns = sql.SQL(", ").join(
                    [sql.Identifier(column) for column in header]
                    + [
                        sql.Identifier("_city"),
                        sql.Identifier("_source_file"),
                        sql.Identifier("_file_hash"),
                    ]
                )
                select_values = sql.SQL(", ").join(
                    [sql.Identifier(column) for column in header]
                    + [
                        sql.Placeholder(),
                        sql.Placeholder(),
                        sql.Placeholder(),
                    ]
                )
                cur.execute(
                    sql.SQL("INSERT INTO {} ({}) SELECT {} FROM {}").format(
                        target_table,
                        insert_columns,
                        select_values,
                        temp_table,
                    ),
                    (city, path.name, file_hash),
                )
                inserted_rows = cur.rowcount

            if inserted_rows != report.row_count:
                raise RuntimeError(
                    f"inserted {inserted_rows} rows but validated "
                    f"{report.row_count}"
                )

            upsert_loaded(
                conn,
                spec.name,
                city,
                scrape_id,
                path.name,
                file_hash,
                inserted_rows,
            )

    return LoadResult(
        dataset=spec.name,
        city=city,
        scrape_id=scrape_id,
        file_hash=file_hash,
        row_count=inserted_rows,
        status="replaced" if deleted_rows else "loaded",
    )
