# Stage 13 - Observability & Logging

## Stage Objective
Implement production-style observability with API metrics, structured logs, data quality monitoring, and alert rules.

## Why This Stage Matters
- Makes API behavior measurable (latency, throughput, error rate).
- Enables incident response with request-level structured logs.
- Tracks data quality outcomes as auditable records.
- Adds alert conditions for failure and degradation states.

## Implemented Components

### 1) Structured API Logging
- File: `api/fastapi/app/main.py`
- Added HTTP middleware that emits JSON log events for every request with:
  - `request_id`
  - method/path/status
  - latency in milliseconds
  - client address
- Response includes `x-request-id` header for correlation.

### 2) Expanded API Metrics Instrumentation
- Existing Prometheus metrics now captured consistently for all endpoints through middleware:
  - `fastapi_requests_total{method,endpoint,status}`
  - `fastapi_request_latency_seconds{method,endpoint}`
- Existing `/metrics` endpoint continues exposing metrics for Prometheus scraping.

### 3) Data Quality Monitoring
- File: `scripts/monitor_data_quality.py`
- Executes warehouse checks against `gold.mart_city_daily_kpis`:
  - non-empty table
  - freshness check (`max(event_date)` within threshold)
  - no negative `gross_fare_total`
- Writes every check result to `metadata.data_quality_audit`.
- Exits non-zero when any rule fails to support automation/alerts in future stages.

### 4) Prometheus Alert Rules
- File: `docker/prometheus/alerts.yml`
- Added alerts:
  - `FastAPIHealthMissing` (existing)
  - `FastAPIHighErrorRate` (>5% 5xx over 5m)
  - `FastAPIHighP95Latency` (p95 > 1.5s over 10m)

### 5) Monitoring API Endpoint
- File: `api/fastapi/app/main.py`
- Added `GET /api/v1/monitoring/data-quality/latest?limit=20`
  - returns latest rows from `metadata.data_quality_audit`
  - supports direct observability checks from API consumers.

### 6) Unified Pipeline Run Audit
- Files:
  - `scripts/pipeline_audit.py`
  - `scripts/load_kafka_to_postgres.py`
  - `scripts/monitor_data_quality.py`
  - `vector/pipeline/build_and_index_vectors.py`
  - `rag/assistant/ride_intelligence_assistant.py`
  - `ml/feature_pipeline/build_feature_tables.py`
  - `ml/training/train_demand_model.py`
  - `ml/training/train_surge_model.py`
  - `ml/training/train_fraud_model.py`
  - `ml/training/train_churn_model.py`
  - `scripts/run_dbt_with_audit.py`
- Every monitored run now writes to `metadata.pipeline_run_audit` with:
  - `run_id`, `pipeline_name`, `stage_name`
  - `status` (`running` → `success`/`failed`)
  - `started_at`, `ended_at`
  - `details` JSON including processed counts, failures, duration, and optional errors.
- Added API read endpoint:
  - `GET /api/v1/monitoring/pipeline-runs/latest?limit=20`

Covered pipelines now include ingestion, quality checks, vector indexing, RAG assistant, ML feature/training flows, and dbt warehouse execution.

## Local Runbook
1. Rebuild and restart FastAPI + monitoring stack:
   - `docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.monitoring.yml up -d --build`
2. Run data quality monitor:
   - `python scripts/monitor_data_quality.py`
3. Read recent quality audits via API:
   - `GET http://localhost:8000/api/v1/monitoring/data-quality/latest?limit=20`
4. Read recent pipeline run audits via API:
  - `GET http://localhost:8000/api/v1/monitoring/pipeline-runs/latest?limit=20`
5. Check Prometheus targets/alerts:
   - `http://localhost:9090/targets`
   - `http://localhost:9090/alerts`
6. Explore dashboards:
   - `http://localhost:3000`

## Exit Criteria (Stage 13)
- Structured per-request API logs are emitted.
- Metrics are exported and scraped by Prometheus.
- Alert rules cover service-down, high error rate, and high latency.
- Data quality checks are persisted and queryable.

## Next Stage Preview (Stage 14)
Enterprise scalability for multi-city expansion: throughput strategy, partitioning, and scaling topology.
