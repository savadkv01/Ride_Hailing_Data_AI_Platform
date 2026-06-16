# Stage 14 – Enterprise Scalability & Multi-City Expansion

## Goal
Scale the platform from single-region/local simulation into an enterprise-ready, multi-city architecture that supports higher throughput, predictable latency, and controlled city onboarding.

## Scope
- Throughput and partition strategy for streaming and storage layers
- Multi-city ingestion/transform conventions
- Capacity tiers and SLO targets
- Operational controls for adding new cities without breaking canonical models

## Target Outcomes
- City expansion framework from `2` cities to `N` cities with controlled rollout
- Stable ingestion and transformation latency under higher event rates
- Consistent canonical schema and dimensional semantics across all onboarded cities
- Clear configuration-driven city onboarding contract

## Scalability Strategy

### 1) Kafka and Streaming Partitioning
- Topic partitioning dimension: `city_id` + event key (`trip_id`/`driver_id` depending on stream)
- Retention by topic criticality:
  - high-volume telemetry (shorter retention)
  - financial/compliance events (longer retention)
- Consumer scaling policy:
  - ingest consumers scale with partition count
  - one primary consumer group per pipeline stage to avoid duplicate writes

### 2) Lakehouse Layout
- Bronze/Silver/Gold physical partitioning baseline:
  - `city_id`
  - `event_date` (derived from event timestamp)
- City-level quarantine monitoring to isolate bad data without blocking global pipelines
- Backfill policy by city and date window

### 3) Warehouse and dbt Scaling
- Keep canonical staging contract stable (`staging.silver_canonical_events`)
- Incremental models remain default for large fact tables
- City-aware test packs:
  - row volume anomaly checks
  - null/unique checks per city slice

### 4) ML and AI Layer Scaling
- Feature tables support city-specific segmentation and global aggregates
- Model strategy:
  - shared global baseline model
  - city-tuned models where performance justifies split
- Vector/RAG indexing:
  - include `cityId` metadata in vector payloads
  - retrieval can be city-filtered for better grounding

## Multi-City Onboarding Contract
Every new city must provide:
- source mapping to canonical model
- timezone and currency metadata
- event quality thresholds (completeness, timeliness)
- rollout mode (`pilot`, `scaled`, `enterprise`)

Onboarding sequence:
1. Add city config
2. Validate synthetic + open data mapping
3. Run ingestion and normalization smoke tests
4. Run dbt + DQ gates
5. Enable ML/vector/RAG for the city
6. Promote city tier from `pilot` to `scaled`

## Capacity Tiers (Reference)
- `pilot`: <= 10k events/hour/city
- `scaled`: <= 100k events/hour/city
- `enterprise`: > 100k events/hour/city

## SLO Baselines (Local/Pre-Prod Targets)
- Ingestion availability: >= 99.5%
- End-to-end batch freshness (city daily): <= 30 minutes from schedule
- Critical API health endpoint availability: >= 99.9%
- Data quality pass rate for required tests: >= 99%

## Deliverables Added in Stage 14
- City scaling config: `config/scaling/multi_city_expansion.yaml`
- Stage theory and execution doc: this file
- Architecture note updates to reflect resilient multi-city operation
- Airflow e2e now creates per-city open-data tasks for enabled/supported cities from city registry (`NYC`, `CHICAGO`) using `scripts/run_open_data_city_batch.py`

## Airflow Hook (Implemented)
- DAG: `orchestration/airflow/dags/ride_hailing_e2e_orchestrator.py`
- Registry source: `config/scaling/multi_city_expansion.yaml`
- Behavior:
  - loads `city_registry`
  - selects enabled cities with supported open-data source
  - creates task IDs like `open_data_batch_nyc`, `open_data_batch_chicago`
  - wires all city tasks upstream of `synthetic_publish`

## Exit Criteria for Stage 14
- At least one additional city can be onboarded through configuration only
- Pipeline behavior remains deterministic when city count increases
- Observability includes per-city success/failure visibility
- Throughput/latency baselines captured and documented
