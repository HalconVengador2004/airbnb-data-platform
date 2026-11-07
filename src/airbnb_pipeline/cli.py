import argparse
import sys
from typing import Sequence

from airbnb_pipeline import config
from airbnb_pipeline.datasets import DATASET_SPECS
from airbnb_pipeline.db import apply_sql_file, get_connection
from airbnb_pipeline.ingestion.loader import load_dataset
from airbnb_pipeline.validation import (
    ValidationError,
    ValidationReport,
    validate_dataset,
)


def _selected_cities(city: str | None) -> tuple[str, ...]:
    return (city,) if city else config.CITIES


def _print_report(report: ValidationReport) -> None:
    print(
        f"{report.path.name}: rows={report.row_count} "
        f"scrape_ids={report.scrape_ids} "
        f"price_parsed={report.price_parsed} "
        f"price_null={report.price_null} "
        f"price_failed={report.price_failed} "
        f"duplicate_keys={report.duplicate_keys}"
    )
    for warning in report.warnings:
        print(f"  warning: {warning}")
    for error in report.errors:
        print(f"  error: {error}")
    if report.error_count > len(report.errors):
        print(f"  ... {report.error_count - len(report.errors)} more error(s)")


def command_init_db(args: argparse.Namespace) -> int:
    try:
        conn = get_connection()
    except Exception as exc:
        print(f"database connection failed: {exc}", file=sys.stderr)
        return 1

    try:
        apply_sql_file(conn, config.SQL_DIR / "001_init.sql")
    finally:
        conn.close()

    print("Database initialized.")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    spec = DATASET_SPECS[args.dataset]
    failed = False

    for city in _selected_cities(args.city):
        path = config.source_file(spec.name, city)
        try:
            report = validate_dataset(path, spec)
        except ValidationError as exc:
            failed = True
            _print_report(exc.report)
        else:
            _print_report(report)

    return 1 if failed else 0


def command_ingest(args: argparse.Namespace) -> int:
    spec = DATASET_SPECS[args.dataset]

    try:
        conn = get_connection()
    except Exception as exc:
        print(f"database connection failed: {exc}", file=sys.stderr)
        return 1

    failed = False
    try:
        for city in _selected_cities(args.city):
            path = config.source_file(spec.name, city)
            try:
                result = load_dataset(conn, spec, city, path)
            except ValidationError as exc:
                failed = True
                _print_report(exc.report)
            except Exception as exc:
                failed = True
                print(f"{city}: failed: {exc}")
            else:
                print(
                    f"{city}: {result.status} rows={result.row_count} "
                    f"scrape_id={result.scrape_id}"
                )
    finally:
        conn.close()

    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="airbnb-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db")
    init_db.set_defaults(func=command_init_db)

    for name, func in (("validate", command_validate), ("ingest", command_ingest)):
        subparser = subparsers.add_parser(name)
        subparser.add_argument(
            "--dataset",
            choices=sorted(DATASET_SPECS),
            default="listings",
        )
        subparser.add_argument("--city", choices=config.CITIES)
        subparser.set_defaults(func=func)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
