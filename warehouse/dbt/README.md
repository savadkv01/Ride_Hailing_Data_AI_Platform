# Stage 8 - dbt Dimensional Warehouse

This dbt project materializes conformed dimensions and fact tables in PostgreSQL.

## Key models
- Dimensions: rider, driver, vehicle, city, time, promotion, payment method
- Facts: trip, driver earnings, payment, review, fraud, operational event
- Marts: city daily metrics

## Output schemas
- `staging`: staging views (for example `staging.stg_silver_canonical_events`)
- `gold`: conformed dimensions, facts, and marts

The project overrides dbt default schema naming so schemas are created exactly as configured (`staging`, `gold`) rather than prefixed forms like `analytics_staging`.

## Expected source table
The project expects canonical events in PostgreSQL table:
- `staging.silver_canonical_events`

## Quick start
1. Copy `profiles.example.yml` to your dbt profile location as `profiles.yml`.
2. Ensure PostgreSQL is running and `staging.silver_canonical_events` is loaded.
3. Run:
   - `dbt debug`
   - `dbt run`
   - `dbt test`

Alternative (audit-enabled run):
- `python scripts/run_dbt_with_audit.py`

This writes dbt run lifecycle status/details to `metadata.pipeline_run_audit`.

## Cleanup legacy schemas
If you previously ran models before medallion schema naming was enabled, clean old schemas with:

- `powershell -ExecutionPolicy Bypass -File scripts/cleanup-legacy-warehouse.ps1`

This removes legacy schemas `analytics_analytics`, `analytics_staging`, and old `analytics` if present.
