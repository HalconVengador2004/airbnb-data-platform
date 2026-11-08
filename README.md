# airbnb-data-platform
Data Engineering project to practice using various modern data technologies on a house rental data platfrom

## Overview

Analytics platform for short-term rental listings published by Inside Airbnb for Madrid and Euskadi. The platform ingests the public listing snapshots, validates them, preserves the source data, and prepares the project for dbt models, Airflow orchestration, and Power BI reporting.

Phase 0, Phase 1, and Phase 2 are implemented and verified against a live PostgreSQL 17 instance: infrastructure, raw ingestion, validation, an idempotent transactional loader, and a dbt staging layer.

## Architecture

```
data/raw/*.csv
      |
      v
raw.listings              all source columns as TEXT + ingestion metadata
      |
      v
dbt staging               typed and cleaned models (Phase 2)
      |
      v
dbt marts                 analytical models (Phase 3)
      |
      v
Power BI                  reporting layer (Phase 5)
```

Airflow will orchestrate the same steps in Phase 4.

## Repository layout

```
.
├── docker-compose.yml
├── infra/postgres/init/01_databases.sql
├── sql/001_init.sql
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── macros/
│   ├── models/staging/
│   └── tests/
├── src/airbnb_pipeline/
│   ├── cli.py
│   ├── config.py
│   ├── datasets.py
│   ├── db.py
│   ├── parsing.py
│   ├── ingestion/
│   └── validation/
├── tests/unit/
├── tests/integration/
└── data/raw/
```

## Prerequisites

- Docker with Docker Compose
- Python 3.10 or newer
- The existing `.venv` environment
- The two source files:
  - `data/raw/listings_madrid.csv`
  - `data/raw/listings_euskadi.csv`

## Setup

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m airbnb_pipeline init-db
```

The local commands use `PYTHONPATH=src`, so the existing virtual environment does not need build-tool upgrades. The `pyproject.toml` file also supports a normal package install in future Docker images.

## Commands

```powershell
$env:PYTHONPATH = "src"

.\.venv\Scripts\python.exe -m airbnb_pipeline validate
.\.venv\Scripts\python.exe -m airbnb_pipeline ingest
.\.venv\Scripts\python.exe -m pytest
```

Load one city only:

```powershell
.\.venv\Scripts\python.exe -m airbnb_pipeline validate --city madrid
.\.venv\Scripts\python.exe -m airbnb_pipeline ingest --city madrid
```

Run the database integration test:

```powershell
$env:RUN_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -m integration
```

## dbt setup (Phase 2)

Install the dbt dependencies into the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install "dbt-core==1.11.17" "dbt-postgres==1.11.0"
```

`dbt-core` and `dbt-postgres` are also declared in the `dbt` optional dependency group in `pyproject.toml`. Installing dbt downgrades `python-dateutil` from `3.0.0` to `2.9.0.post0`, because `dbt-common` requires `python-dateutil<3.0`. `pandas==2.3.3` requires `python-dateutil>=2.8.2`, so it remains compatible.

The dbt profile reads `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` from the environment. `dbt/profiles.yml` contains only `env_var()` references and no credentials. The `.env` file remains gitignored and is loaded for the command with `dotenv`.

Run the dbt commands from the repository root:

```powershell
.\.venv\Scripts\dotenv.exe run -- .\.venv\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
```

```powershell
.\.venv\Scripts\dotenv.exe run -- .\.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt
```

```powershell
.\.venv\Scripts\dotenv.exe run -- .\.venv\Scripts\dbt.exe test --project-dir dbt --profiles-dir dbt
```

## Staging model (Phase 2)

`staging.stg_listings` is a view over the `raw.listings` source. It keeps one row per `(_city, scrape_id, id)`, selects every source column explicitly, and does not filter records. Raw text is preserved for fields that need interpretation, with derived columns added alongside.

- **Dates**: `last_scraped`, `calendar_last_scraped`, `first_review`, `last_review`, `host_since`, `price_quote_checkin_date`, and `price_quote_checkout_date` are cast to `DATE` only when the value is ISO `YYYY-MM-DD` and passes PostgreSQL `pg_input_is_valid(value, 'date')`. The regex enforces the ISO form; the function rejects semantically invalid dates such as `2026-02-30`. `calendar_updated` stays `TEXT` because all current values are null and the source does not provide reliable date semantics.
- **Price**: `price_raw` preserves the source text. `price_eur` is the parsed `NUMERIC(12,2)` amount, `price_currency` is `EUR`, and `price_parse_status` is `ok`, `null`, or `invalid`. The value is EUR because `price_quote_raw` reports `"currency": "EUR"`; the `$` glyph is a source formatting artifact and no currency conversion is performed.
- **Bathrooms**: `bathrooms_text` is preserved exactly. `bathrooms_count` is numeric, `bathroom_type` is `shared`, `private`, `not_specified`, `none`, or `unknown`, and `is_half_bath` marks half-bath wording. All half-baths have a count of `0.5`; `Shared half-bath` and `Private half-bath` keep their shared/private distinction; `No bathroom` has a count of `0`. Generic `1 bath` is not guessed to be shared or private.
- **Amenities**: `amenities_raw` preserves the JSON text. `amenities_json` is a `JSONB` array, `amenities_count` is its length, and `amenities_parse_status` is `ok`, `empty`, or `invalid`. Parsing uses PostgreSQL JSON validity checks, so malformed values are surfaced instead of discarded.
- **License**: `license_raw` preserves the text. `license_has_text`, `license_mentions_exempt`, `license_mentions_regional`, `license_mentions_national`, and `license_flag` are descriptive text flags only. They do not assert legal compliance, validity, or registration status.
- **Identifiers and metadata**: `id`, `scrape_id`, `host_id`, and `host_profile_id` stay `TEXT`. `_city`, `_source_file`, `_file_hash`, and `_loaded_at` are preserved as ingestion metadata.

The model is materialized as a **view** because it is a thin 1:1 transformation over an already-materialized raw table. This avoids duplicate storage, always reflects the latest raw snapshot, and keeps the parsing cost modest at 29,357 rows. Marts in Phase 3 will choose materializations per model based on volume, query cost, and freshness.

Tests include schema tests (`not_null`, `accepted_values`), a record-integrity test using a `FULL OUTER JOIN` on `(_city, scrape_id, id)`, a unique-grain test, a raw-value preservation test, parse-consistency tests for price/bathrooms/amenities/license, and a source-format test covering every typed date, boolean, integer, and numeric column.

## Data notes

- Each CSV is one scrape snapshot. The raw table grain is `(_city, scrape_id, id)`.
- The Madrid and Euskadi files were scraped on different dates and have different `scrape_id` values.
- Madrid is a city with 21 districts; Euskadi is an autonomous community with three provinces. Cross-city comparisons are city-versus-region comparisons.
- `price` is preserved exactly as text (exposed as `price_raw` in staging). The parser returns a `Decimal` and the detected currency marker without converting currencies. The source `price` values use a `$` marker, while `price_quote_raw` reports `EUR`.
- Null `price` values are preserved and reported; they are not imputed.
- `bathrooms` is entirely null in these snapshots, while `bathrooms_text` is populated.
- `host_since`, `instant_bookable`, and several host-response columns are entirely null in these snapshots.
- The original CSV files are never modified.

## Verification

```powershell
docker compose exec postgres psql -U airbnb -d warehouse -c "SELECT _city, count(*) FROM raw.listings GROUP BY _city ORDER BY _city;"
docker compose exec postgres psql -U airbnb -d warehouse -c "SELECT dataset, city, scrape_id, row_count, status FROM ingestion.file_manifest ORDER BY city;"
```

Expected row counts after the first successful load:

- `madrid`: 23,109
- `euskadi`: 6,248
- total: 29,357

Running `ingest` again should report `skipped` for both files and leave the row counts unchanged.

## Phase status

- Phase 0: complete
- Phase 1: complete
- Phase 2: complete, dbt staging model and tests
- Phase 3: next, dbt marts (not started)
