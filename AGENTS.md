# AGENTS.md

## Project

Airbnb analytics platform for Inside Airbnb listing snapshots (Madrid and
Euskadi). Python validates and loads the raw CSVs into PostgreSQL; dbt builds
the staging layer. Phases 0, 1, and 2 are complete.

`README.md` is the canonical source for setup, architecture, data notes, and
detailed verification. Keep this file focused on rules, invariants, and the
commands agents need.

## Status and scope

- Phase 0 (infrastructure): complete.
- Phase 1 (raw ingestion): complete.
- Phase 2 (dbt staging): complete.
- Phase 3 and later: not started. Do not begin a new phase without explicit
  approval. You may identify dependencies, risks, and recommended next work.

## Architecture

```
data/raw/*.csv
  -> raw.listings          all source columns TEXT + ingestion metadata
  -> staging.stg_listings  typed and cleaned dbt view (Phase 2)
  -> future marts          not implemented
```

- Raw data is immutable; cleaning, typing, and interpretation happen in dbt.
- PostgreSQL 17 runs in Docker Compose as `airbnb-postgres`.
- Python and dbt run on the Windows host; Python connects to
  `localhost:5432`, the published container port.

## Stack

- Python 3.10+ (`src/` layout, package `airbnb_pipeline`)
- PostgreSQL 17 via Docker Compose
- dbt-core 1.11.17 and dbt-postgres 1.11.0
- psycopg2-binary, python-dotenv, pytest
- Airflow and Power BI are not implemented.

## Layout

```
src/airbnb_pipeline/
  cli.py          init-db, validate, ingest
  config.py       environment, paths, CITIES
  datasets.py     LISTINGS_COLUMNS contract and DatasetSpec registry
  db.py           psycopg2 connection and SQL file application
  parsing.py      strict price parser
  validation/     streaming CSV validators
  ingestion/      hash-based manifest and transactional loader
sql/              numbered DDL; init-db applies 001_init.sql
dbt/              dbt project: models/staging, tests, macros, profiles.yml
tests/unit/       no database required
tests/integration/ requires PostgreSQL (RUN_INTEGRATION=1)
scripts/          ad-hoc inspection; not imported by the package
infra/postgres/init/  container initialization SQL
data/raw/         immutable source CSVs (gitignored)
dags/             currently empty
```

## Workflows

Run all commands from the repository root in PowerShell.

Setup:

```powershell
Copy-Item .env.example .env   # first time only
docker compose up -d postgres
$env:PYTHONPATH = "src"
```

Python pipeline:

```powershell
.\.venv\Scripts\python.exe -m airbnb_pipeline init-db
.\.venv\Scripts\python.exe -m airbnb_pipeline validate
.\.venv\Scripts\python.exe -m airbnb_pipeline ingest
```

Add `--city madrid` or `--city euskadi` to restrict `validate` or `ingest`.

dbt, from the repository root:

```powershell
.\.venv\Scripts\dotenv.exe run -- .\.venv\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
.\.venv\Scripts\dotenv.exe run -- .\.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt
.\.venv\Scripts\dotenv.exe run -- .\.venv\Scripts\dbt.exe test --project-dir dbt --profiles-dir dbt
```

Python tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Enable the PostgreSQL integration test, then rerun:

```powershell
$env:RUN_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

## Verification

Expected raw counts: Madrid 23,109; Euskadi 6,248; total 29,357. The manifest
must contain two `loaded` rows, and re-running `ingest` must report `skipped`.

```powershell
docker compose exec -T postgres psql -U airbnb -d warehouse -c "SELECT _city, count(*) FROM raw.listings GROUP BY _city ORDER BY _city;"
docker compose exec -T postgres psql -U airbnb -d warehouse -c "SELECT dataset, city, scrape_id, row_count, status FROM ingestion.file_manifest ORDER BY city;"
```

`dbt build` must pass all models and tests. `staging.stg_listings` must have
29,357 rows and preserve the raw `price`, `bathrooms_text`, `amenities`, and
`license` values. The dbt record-integrity test checks this with a
`FULL OUTER JOIN` on `(_city, scrape_id, id)`.

## Engineering rules

- Prefer the smallest solution; avoid speculative abstractions.
- Every pipeline step must be idempotent and safe to re-run.
- Keep raw and transformed data separate; the raw layer preserves source
  fidelity.
- Data quality checks must be explicit, automated, and fail loudly.
- Never silently drop, coerce, skip, or impute rows.
- Any filtering or rejection must be counted and reported with a reason.
- Record non-obvious decisions such as grain, parsing rules, schema, and
  materialization.

## Python conventions

- Keep the `src/` layout and `airbnb_pipeline.*` imports.
- Use type hints and dataclasses; prefer the standard library.
- Do not upgrade or replace `.venv`.
- Do not add, remove, or upgrade dependencies without explaining why and
  obtaining approval. `pyproject.toml` declares runtime dependencies;
  `requirements.txt` records pinned versions and may be updated deliberately
  when dependencies change.
- Use psycopg2 with `%s` placeholders and `psycopg2.sql` for identifiers.
  Never build SQL by string concatenation.
- Keep CSV validation streaming; do not load whole files into pandas in
  pipeline code.
- Fail loudly on invalid data.

## SQL conventions

- Schemas: `raw` for source data, `ingestion` for pipeline metadata, and
  `staging` for dbt models. No `marts` schema exists yet.
- DDL must be idempotent (`IF NOT EXISTS`) and numbered
  `sql/00N_description.sql`.
- Raw source columns stay `TEXT`. Pipeline metadata is typed and prefixed
  with `_`.
- Do not edit an applied migration in place; add a new numbered file.
  `init-db` currently applies only `sql/001_init.sql`.
- Parameterize all values and quote identifiers with `psycopg2.sql`.
- Never run `DROP`, `TRUNCATE`, or an unqualified `DELETE` against `warehouse`
  without explicit approval.

## dbt conventions

- The project lives in `dbt/` and must be run from the repository root with
  `--project-dir dbt --profiles-dir dbt`.
- Staging models are `stg_*` in `dbt/models/staging/`.
- Declare sources in `_sources.yml`; document and test keys and statuses.
- One model per file, lowercase snake_case; no `SELECT *` in models.
- Keep staging thin: rename, cast, and clean. Put business logic in marts.
- `stg_listings` is a view. Justify materialization choices by data volume,
  query cost, and freshness.
- `dbt/profiles.yml` contains only `env_var()` references. Never commit
  credentials.
- `dbt/.user.yml`, `dbt/target/`, and `dbt/logs/` are local artifacts.

## Data rules

- `data/raw/*.csv` are immutable. Never edit, move, or delete them.
- Raw grain is `(_city, scrape_id, id)`, enforced by a unique index.
- Each file must contain exactly one `scrape_id`; validation rejects mixed
  scrapes.
- `price` is text. Preserve the raw value; parse to `Decimal` plus a currency
  marker; reject ambiguous formats; never guess, impute, or convert
  currencies.
- Nulls are meaningful. Do not impute sparse columns such as `price`,
  `bathrooms`, or `host_since`.
- Madrid is a city; Euskadi is an autonomous community. Treat cross-city
  comparisons as city-versus-region.
- Idempotency is by SHA-256 file hash: the same hash means `skipped`; a new
  hash for the same `scrape_id` replaces that snapshot.
- Pipeline-owned columns (`_city`, `_source_file`, `_file_hash`, `_loaded_at`)
  must never be populated from source data.

## Git

- Default branch: `master`. Use short-lived branches: `feat/…`, `fix/…`,
  `docs/…`, `test/…`, `chore/…`.
- Use Conventional Commits, imperative and scoped.
- Never commit `.env`, `data/`, `.venv/`, logs, or generated artifacts.
- Do not commit or push unless the user explicitly asks. Never force-push or
  rewrite history.

## Agent workflow and safety

1. Read `README.md` and this file before changing code.
2. State the plan and exact files for multi-file changes.
3. Do not start a new phase without explicit approval.
4. Do not modify `data/raw/*.csv`, `.env`, or `.venv/` without approval.
5. Do not add, remove, or upgrade dependencies without approval.
6. Do not add subagents, skills, plugins, or config unless asked.
7. Never print secrets or `.env` contents.
8. Integration tests must use isolated values such as `integration_test` and
   clean up afterward. Never write test data into `madrid` or `euskadi`.
9. Run the relevant tests before reporting success and include the commands
   and actual results.
10. If verification is blocked, say so; do not claim unverified results.
11. Do not commit or push automatically.
