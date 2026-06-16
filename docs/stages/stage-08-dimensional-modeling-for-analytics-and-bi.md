# Stage 8 - Dimensional Modeling for Analytics and BI

## Stage Objective
Build an analytics-ready dimensional warehouse layer using dbt on PostgreSQL so business KPIs are queryable with conformed dimensions, consistent facts, and testable data contracts.

## Why This Stage Matters
- Streaming silver data is event-centric and not always BI-friendly.
- Business users need stable semantic entities (dimensions/facts) with clear grain.
- dbt introduces reproducible SQL transformations, documentation, and tests.

## Inputs and Outputs
- Input: Silver canonical events (`stg_silver_canonical_events` from Stage 7 output).
- Output:
  - Dimensions: `dim_city`, `dim_rider`, `dim_driver`, `dim_vehicle`, `dim_promotion`, `dim_payment_method`, `dim_time`
  - Facts: `fact_trip`, `fact_driver_earnings`, `fact_payment`, `fact_review`, `fact_fraud`, `fact_operational_event`
  - Mart: `mart_city_daily_kpis`

## Schema Convention
- `staging` schema: staging models and source-facing views.
- `gold` schema: dimensions, facts, and marts used by BI and semantic APIs.
- dbt schema generation is overridden so schemas are used exactly as named (no automatic prefix pattern like `<target>_<custom>`).

## Grain Definitions
- `fact_trip`: one row per trip-level event key.
- `fact_driver_earnings`: one row per trip earning view.
- `fact_payment`: one row per payment event.
- `fact_review`: one row per review event.
- `fact_fraud`: one row per fraud case event.
- `fact_operational_event`: one row per canonical event.
- `dim_time`: hour grain using `YYYYMMDDHH` integer key.

## dbt Project Structure Implemented
- `warehouse/dbt/dbt_project.yml`
- `warehouse/dbt/models/staging/*`
- `warehouse/dbt/models/dimensions/*`
- `warehouse/dbt/models/facts/*`
- `warehouse/dbt/models/marts/*`

## Testing and Quality Controls
Implemented model-level schema tests:
- Primary surrogate keys: `not_null` + `unique`
- Core business IDs: `not_null`
- Mart keys: `not_null`

These are starting tests; later stages can add relationship and accepted-value tests.

## Incremental Strategy
Fact models are configured incrementally using `event_time` watermark filters:
- Prevents full reload on each run.
- Enables near-real-time rebuild patterns.
- Can be tuned later for late-arriving event backfill windows.

## Operational Runbook (Local)
From `warehouse/dbt`:
1. `dbt deps`
2. `dbt debug`
3. `dbt run`
4. `dbt test`
5. `dbt docs generate`

## Azure Mapping
- Local dbt + PostgreSQL -> dbt Cloud/Core + Azure Database for PostgreSQL / Synapse SQL dedicated model layer.
- Local mart output -> Power BI semantic models.

## Interview Talking Points
- “We separated streaming canonicalization from BI semantics to keep each layer purpose-built.”
- “Conformed dimensions ensure metrics consistency across trip, payment, fraud, and review domains.”
- “dbt tests converted model assumptions into executable contracts.”
- “Incremental fact builds balanced freshness and cost.”

## Exit Criteria (Stage 8)
- dbt project scaffolded and organized by staging/dimensions/facts/marts.
- Core dimensions and facts implemented from silver canonical events.
- Baseline schema tests added.
- KPI mart created for dashboard consumption.

## Next Stage Preview (Stage 9)
Serve semantic BI APIs and dashboards (FastAPI + Grafana/BI adapters) over curated marts and facts.
