# airbnb-data-platform
Data Engineering project to practice using various modern data technologies on a house rental data platfrom

## Overview

Analytics platform for short-term rental listings published by Inside Airbnb for Madrid and Euskadi. The platform ingests the public listing snapshots, validates them, preserves the source data, and prepares the project for dbt models, Airflow orchestration, and Power BI reporting.

Phase 0 and Phase 1 are implemented and verified against a live PostgreSQL 17 instance: infrastructure, raw ingestion, validation, and an idempotent transactional loader.

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

## Data notes

- Each CSV is one scrape snapshot. The raw table grain is `(_city, scrape_id, id)`.
- The Madrid and Euskadi files were scraped on different dates and have different `scrape_id` values.
- Madrid is a city with 21 districts; Euskadi is an autonomous community with three provinces. Cross-city comparisons are city-versus-region comparisons.
- `price` is preserved exactly as text. The parser returns a `Decimal` and the detected currency marker without converting currencies. The source `price` values use a `$` marker, while `price_quote_raw` reports `EUR`.
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
- Phase 2: next, dbt staging models and tests
