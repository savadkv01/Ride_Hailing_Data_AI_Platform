# Local Access and Operations Reference

This document lists local URLs, credentials, container/service names, and common commands for the Ride-Hailing Data + AI Platform.

## 1) Primary URLs

| Component | URL | Notes |
|---|---|---|
| FastAPI | http://localhost:8000 | Main API service |
| Streamlit AI UI | http://localhost:8501 | End-user AI interface |
| FastAPI Health | http://localhost:8000/health | Liveness check |
| FastAPI Metrics | http://localhost:8000/metrics | Prometheus scrape target |
| Airflow UI | http://localhost:8088 | DAG orchestration UI |
| Spark Master UI | http://localhost:8081 | Cluster/job overview |
| Prometheus | http://localhost:9090 | Metrics + alert rule evaluation |
| Grafana | http://localhost:3000 | Dashboards/alerts |
| Weaviate Readiness | http://localhost:8080/v1/.well-known/ready | Vector DB health |
| Weaviate API Root | http://localhost:8080/v1 | Vector API |
| Ollama | http://localhost:11434 | LLM runtime endpoint |
| Kafka External | localhost:9094 | Producer/consumer from host |
| PostgreSQL | localhost:5432 | Warehouse DB |
| MongoDB | localhost:27017 | Operational/semi-structured store |

## 2) Default Local Credentials

> Use environment files under `docker/compose/` and rotate for non-local environments.

| Service | Username | Password | Source |
|---|---|---|---|
| Airflow UI | admin | admin | `docker/compose/docker-compose.airflow.yml` |
| Grafana | admin | admin | `docker/compose/.env.local` |
| PostgreSQL | ride_admin | ride_password | `docker/compose/.env.local` |
| MongoDB (root) | ride_mongo_admin | ride_mongo_password | `docker/compose/.env.local` |

## 3) Core Docker Compose Files

| File | Purpose |
|---|---|
| `docker/compose/docker-compose.base.yml` | Core platform services (Kafka, Postgres, MongoDB, Weaviate, Ollama, FastAPI) |
| `docker/compose/docker-compose.spark.yml` | Spark master + workers |
| `docker/compose/docker-compose.monitoring.yml` | Prometheus + Grafana |
| `docker/compose/docker-compose.airflow.yml` | Airflow scheduler/webserver stack |
| `docker/compose/docker-compose.jobs.yml` | Job images for orchestration (ingestion/warehouse/ml/ai) |

## 4) Key Container Names

| Logical Component | Container Name |
|---|---|
| Kafka | `rh-kafka` |
| PostgreSQL | `rh-postgres` |
| MongoDB | `rh-mongodb` |
| Weaviate | `rh-weaviate` |
| Ollama | `rh-ollama` |
| FastAPI | `rh-fastapi` |
| Streamlit UI | `rh-streamlit-ui` |
| Spark Master | `rh-spark-master` |
| Spark Worker 1 | `rh-spark-worker-1` |
| Spark Worker 2 | `rh-spark-worker-2` |
| Prometheus | `rh-prometheus` |
| Grafana | `rh-grafana` |
| Airflow Postgres | `rh-airflow-postgres` |
| Airflow Scheduler | `rh-airflow-scheduler` |
| Airflow Webserver | `rh-airflow-webserver` |

## 5) Airflow DAGs (Current)

| DAG ID | Purpose |
|---|---|
| `ride_hailing_e2e_orchestrator` | Main end-to-end flow (ingestion -> transform -> ML/vector/RAG -> DQ) |
| `ride_hailing_operational_controls` | Operational toggles (open-data batch, ingestion-only, AI-only, DQ-only, Spark start/stop) |

## 6) Common Startup Commands (from repo root)

### Base + Spark + Monitoring + Airflow
```powershell
docker compose --env-file docker/compose/.env.local \
  -f docker/compose/docker-compose.base.yml \
  -f docker/compose/docker-compose.spark.yml \
  -f docker/compose/docker-compose.monitoring.yml \
  -f docker/compose/docker-compose.airflow.yml up -d
```

### Build orchestration job images
```powershell
docker compose --profile jobs --env-file docker/compose/.env.local \
  -f docker/compose/docker-compose.base.yml \
  -f docker/compose/docker-compose.jobs.yml build ingestion-jobs warehouse-jobs ml-jobs ai-jobs
```

### Check service status
```powershell
docker compose --env-file docker/compose/.env.local \
  -f docker/compose/docker-compose.base.yml \
  -f docker/compose/docker-compose.spark.yml \
  -f docker/compose/docker-compose.monitoring.yml \
  -f docker/compose/docker-compose.airflow.yml ps
```

## 7) Observability + Audit Locations

- Airflow task logs: `logs/airflow/`
- Unified pipeline run audit table: `metadata.pipeline_run_audit` (PostgreSQL)
- Data quality audit table: `metadata.data_quality_audit` (PostgreSQL)
- Inventory reports: `logs/inventory/`

## 8) Environment Files

| File | Typical Use |
|---|---|
| `docker/compose/.env.local` | Local development defaults |
| `docker/compose/.env.enterprise-sim` | Higher-load simulation profile |
| `.env.example` | Template for required configuration |

## 9) Quick API Checks

```powershell
# Health
Invoke-RestMethod http://localhost:8000/health

# City daily KPIs
Invoke-RestMethod "http://localhost:8000/api/v1/analytics/city-daily"

# RAG assistant (Ollama + Weaviate)
Invoke-RestMethod http://localhost:8000/api/v1/rag/ask -Method Post `
  -ContentType application/json `
  -Body '{"question":"How is surge pricing calculated?","top_k":3}'

# ML model predict
Invoke-RestMethod http://localhost:8000/api/v1/models/predict -Method Post `
  -ContentType application/json `
  -Body '{"model_name":"surge_model","features":{"completed_trips":5,"cancelled_trips":1,"gross_fare_total":80,"driver_payout_total":60}}'

# Model status (artifact exists?)
Invoke-RestMethod http://localhost:8000/api/v1/models/status

# MongoDB operational endpoints
Invoke-RestMethod "http://localhost:8000/api/v1/ops/fraud-cases"
Invoke-RestMethod "http://localhost:8000/api/v1/ops/rider-sessions"
Invoke-RestMethod "http://localhost:8000/api/v1/ops/support-tickets"

# Observability
Invoke-RestMethod "http://localhost:8000/api/v1/monitoring/pipeline-runs/latest?limit=10"
Invoke-RestMethod http://localhost:8080/v1/.well-known/ready
```

### Full FastAPI endpoint reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/api/v1/analytics/city-daily` | City KPI mart — completed trips, fares, surge per city/day |
| POST | `/api/v1/rag/ask` | RAG assistant — Weaviate retrieval + Ollama LLM answer |
| POST | `/api/v1/models/predict` | ML inference — demand/surge/fraud/churn models |
| GET | `/api/v1/models/status` | Check which model `.joblib` artifacts exist |
| GET | `/api/v1/ops/fraud-cases` | MongoDB — recent fraud cases (filter: `?city_id=`) |
| GET | `/api/v1/ops/rider-sessions` | MongoDB — rider app session aggregates (filter: `?rider_id=`) |
| GET | `/api/v1/ops/support-tickets` | MongoDB — support tickets (filter: `?city_id=&status=`) |
| POST | `/api/v1/ops/support-tickets` | MongoDB — create a support ticket |
| GET | `/api/v1/monitoring/data-quality/latest` | Recent DQ audit rows |
| GET | `/api/v1/monitoring/pipeline-runs/latest` | Recent pipeline run audit rows |
| GET | `/metrics` | Prometheus scrape target |

## 10) Open-Data Batch Parameters (NYC + Chicago)

`scripts/run_open_data_batch.py`

- `--nyc-year <int>`: NYC TLC year (monthly source file)
- `--nyc-month <1-12>`: NYC TLC month (monthly source file)
- `--chicago-limit <int>`: max Chicago rows to fetch
- `--incremental`: append canonical outputs and deduplicate by `event_id`
- `--for-date <YYYY-MM-DD|today>`: daily mode; Chicago is filtered to that day and NYC month is auto-derived from that date

NYC source resilience behavior:
- If the requested NYC monthly parquet is not yet published (HTTP 403/404), downloader automatically falls back to the most recent available month (up to 24 months lookback) so DAG execution does not fail on publication lag.

### Daily run for today (manual)
```powershell
python scripts/run_open_data_batch.py --for-date today --chicago-limit 200000
```

### Incremental daily run for today (manual)
```powershell
python scripts/run_open_data_batch.py --incremental --for-date today --chicago-limit 200000
```

### Daily run by explicit date (manual)
```powershell
python scripts/run_open_data_batch.py --for-date 2026-03-02 --chicago-limit 200000
```

`ingestion/open_data/download_chicago_taxi.py`

- `--limit <int>`
- `--output-file <path>`
- `--for-date <YYYY-MM-DD|today>`: applies Socrata `$where` filter on `trip_start_timestamp` for one day window

### Airflow behavior

- Open-data tasks in both DAGs now pass `--for-date {{ ds }}`.
- Open-data tasks in both DAGs now pass `--incremental`.
- If the DAG run date is today, the batch pulls Chicago data for today.
- NYC TLC source is monthly; daily mode selects the corresponding month file for that date.

## 11) Latest Full Run Snapshot

- DAG: `ride_hailing_e2e_orchestrator`
- Run ID: `manual_full_20260303_002500_final3`
- Final state: `success`
- Logical date: `2026-03-02T20:13:00+00:00`
- Start/end: `2026-03-02T20:13:01Z` -> `2026-03-02T20:14:33Z`

### Verified task outcomes (high level)

- Ingestion: open-data (skipped by flag), synthetic publish, kafka-to-postgres ✅
- Spark stage task: executed as disabled-path success (resilient mode) ✅
- Warehouse: dbt run + test ✅
- ML: feature build + demand/surge/fraud/churn training ✅
- AI: vector indexing + RAG query ✅
- DQ: quality checks ✅

### Setup stats (PostgreSQL, sampled)

- `staging.silver_canonical_events`: ~5,000 rows, ~928 kB
- `gold.fact_operational_event`: ~5,436 rows, ~1,296 kB
- `gold.fact_trip`: ~4,255 rows, ~1,392 kB
- `ml.feature_rider_churn_daily`: ~2,771 rows, ~272 kB
- `metadata.pipeline_run_audit`: 132 rows, ~152 kB

### Service status summary

- Core services (`kafka`, `postgres`, `mongodb`, `weaviate`, `ollama`, `fastapi`) up and healthy
- Airflow webserver/scheduler/postgres up
- Spark master/workers up
- Monitoring (`prometheus`, `grafana`) up

## 12) How to Add a New City

Use this checklist to onboard a new city safely.

### A) Register city in scaling config

Edit `config/scaling/multi_city_expansion.yaml` and add a new `city_registry` item.

Required fields:
- `city_id` (UPPERCASE short code, example: `SF`)
- `city_name`, `country`, `timezone`, `currency`
- `tier` (`pilot` | `scaled` | `enterprise`)
- `enabled` (`false` first, then `true` after validation)
- `data_sources.open_data` and `data_sources.synthetic`

Example:
```yaml
- city_id: SF
  city_name: San Francisco
  country: US
  timezone: America/Los_Angeles
  currency: USD
  tier: pilot
  enabled: false
  data_sources:
    open_data: pending
    synthetic: true
```

### B) Add source support (if open data is required)

Current open-data task auto-generation supports:
- `nyc_tlc` -> `open_data_batch_nyc`
- `chicago_taxi` -> `open_data_batch_chicago`

If your new city has a different open dataset, add:
1. Downloader under `ingestion/open_data/`
2. Normalizer to canonical schema under `ingestion/open_data/`
3. City handler in `scripts/run_open_data_city_batch.py`

Starter templates are available:
- `ingestion/open_data/download_city_template.py`
- `ingestion/open_data/normalize_city_to_canonical_template.py`

If you only want synthetic data first, keep `data_sources.synthetic: true` and leave `open_data` unsupported until later.

### C) Enable city and rebuild job image

After implementing support, set `enabled: true` for that city and rebuild ingestion jobs:

```powershell
docker compose --profile jobs --env-file docker/compose/.env.local \
  -f docker/compose/docker-compose.base.yml \
  -f docker/compose/docker-compose.jobs.yml build ingestion-jobs
```

### D) Validate DAG picked up city task

```powershell
docker exec rh-airflow-webserver airflow tasks list ride_hailing_e2e_orchestrator
```

You should see a task named `open_data_batch_<city_id_lowercase>` for supported cities.

### E) Run pilot and verify gates

1. Trigger `ride_hailing_e2e_orchestrator` with `run_open_data_batch=true`.
2. Check latest runs in `metadata.pipeline_run_audit`.
3. Check DQ results in `metadata.data_quality_audit`.
4. Confirm row growth in `staging.silver_canonical_events` and gold facts.

### F) Promote city tier

When gates pass consistently:
- change city `tier` from `pilot` -> `scaled`
- tune `capacity_tiers` and ingestion limits as needed
- keep per-city alerts enabled (ingestion and DQ failure thresholds)

### Quick onboarding guardrails

- Keep canonical schema unchanged for new cities.
- Start with `enabled: false`, test in pilot first.
- Prefer config-only onboarding where source type already supported.
- Use synthetic-only onboarding if open data is not yet production-ready.

## 14) Ollama LLM Runtime

Ollama provides on-device LLM inference for embeddings and RAG chat generation.

### Pulled models (current)

| Model | Purpose | Size |
|---|---|---|
| `nomic-embed-text` | Text embeddings for Weaviate indexing + RAG search (768-dim) | 274 MB |
| `llama3.2:3b` | RAG chat generation — answers grounded in retrieved documents | 2.0 GB |

### Check models
```powershell
docker exec rh-ollama ollama list
```

### Pull a model (if missing after container recreate)
```powershell
docker exec rh-ollama ollama pull nomic-embed-text
docker exec rh-ollama ollama pull llama3.2:3b
```

> **Note:** Ollama models are stored in Docker volume `ollama_data` and survive `docker stop`/`docker start`. They are only lost if `docker compose down -v` is run.

### Test embedding
```powershell
Invoke-RestMethod http://localhost:11434/api/embeddings -Method Post `
  -ContentType application/json `
  -Body '{"model":"nomic-embed-text","prompt":"surge pricing"}'
```

## 15) Weaviate Vector Store

- Class: `RideDocument`
- Vector dimensions: **768** (Ollama `nomic-embed-text`)
- Documents indexed: **50** (from 5 synthetic corpus sources: FAQ, reviews, support tickets, policy docs, fraud cases)
- Indexed by: `vector/pipeline/build_and_index_vectors.py`
- Config: `vector/config/vector_index_config.yaml` — `embedding.provider: ollama`

### Re-index after model change
If the embedding model changes dimension, the class must be dropped and recreated:
```powershell
# Drop class
Invoke-RestMethod http://localhost:8080/v1/schema/RideDocument -Method Delete

# Re-index with new model
.venv\Scripts\python.exe vector/pipeline/build_and_index_vectors.py --config vector/config/vector_index_config.yaml
```

### Check object count
```powershell
Invoke-RestMethod "http://localhost:8080/v1/objects?class=RideDocument&limit=1" | Select-Object -ExpandProperty totalResults
```

## 16) MongoDB Operational Store

MongoDB holds semi-structured operational events synced from the Silver layer.

### Collections

| Collection | Contents | Synced from |
|---|---|---|
| `fraud_cases` | Fraud signal events, risk band, fraud score | `staging.silver_canonical_events` WHERE `event_type IN ('fraud_signal', ...)` |
| `rider_app_sessions` | Per-rider session aggregates (completion rate, trip counts) | Aggregated from trip events in Silver |
| `support_tickets` | Support ticket events + manual API inserts | Silver events + `POST /api/v1/ops/support-tickets` |

### Run sync
```powershell
.venv\Scripts\python.exe scripts/sync_events_to_mongodb.py
```
Run this after every Silver load to keep MongoDB current.

### Direct MongoDB access
```powershell
docker exec rh-mongodb mongosh -u ride_mongo_admin -p ride_mongo_password --authenticationDatabase admin ride_hailing_ops --eval "db.fraud_cases.countDocuments()"
```

## 17) Grafana Dashboard

- URL: `http://localhost:3000`
- Default credentials: `admin` / `admin`
- Dashboard: **Dashboards → Ride Hailing Platform → Ride-Hailing Platform KPIs**

### Provisioned files
| File | Purpose |
|---|---|
| `docker/grafana/provisioning/datasources/datasource.yml` | Prometheus (default) + PostgreSQL datasources |
| `docker/grafana/provisioning/dashboards/dashboard.yml` | Dashboard provider config |
| `docker/grafana/provisioning/dashboards/ride_hailing_kpis.json` | Platform KPI dashboard definition |

### Dashboard panels
| Panel | Data source | Query |
|---|---|---|
| City Daily KPIs table | PostgreSQL | `gold.mart_city_daily_kpis` |
| Completed Trips / Gross Fare over time | PostgreSQL | `gold.mart_city_daily_kpis` time series |
| Surge multiplier / Driver payout / Platform revenue / Trips today | PostgreSQL | Latest date in `mart_city_daily_kpis` |
| Recent Pipeline Runs | PostgreSQL | `metadata.pipeline_run_audit` |
| Service Up/Down | Prometheus | `up` metric per job |
| FastAPI Request Rate + p95 Latency | Prometheus | `fastapi_requests_total`, `fastapi_request_latency_seconds_bucket` |

### Network requirement
Grafana must be on both `monitoring_net` AND `platform_core_net` to reach PostgreSQL by hostname.
This is set in `docker/compose/docker-compose.monitoring.yml`. If manually reconnecting:
```powershell
docker network connect platform_core_net rh-grafana
```

## 18) Data Persistence Reference

| Data | Storage | Survives `docker stop/start`? | Survives `docker compose down`? | Lost on `down -v`? |
|---|---|---|---|---|
| PostgreSQL (Gold tables, staging, metadata) | Named volume `postgres_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| Kafka topic messages + offsets | Named volume `kafka_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| MongoDB collections | Named volume `mongodb_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| Weaviate vectors | Named volume `vector_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| Ollama model weights | Named volume `ollama_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| Grafana dashboards/settings | Named volume `grafana_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| Prometheus metrics history | Named volume `prometheus_data` | ✅ Yes | ✅ Yes | ❌ Yes |
| Spark checkpoints | Named volume `spark_checkpoints` | ✅ Yes | ✅ Yes | ❌ Yes |
| Lakehouse Bronze/Silver/Gold parquet | Bind-mount → `lakehouse/` host folder | ✅ Yes | ✅ Yes | ✅ Yes (host folder) |
| ML model artifacts (`*.joblib`) | Bind-mount → `ml/artifacts/` host folder | ✅ Yes | ✅ Yes | ✅ Yes (host folder) |

> **Warning:** Never run `docker compose down -v` unless intentionally resetting the entire platform. All named volumes will be destroyed.

## 13) Contract Validation Controls (Stage 15)

Canonical contract file:
- `config/contracts/op_trip_events_contract_v1.json`

Validator module:
- `scripts/contract_validator.py`

Enforced paths:
- `ingestion/open_data/normalize_nyc_to_canonical.py`
- `ingestion/open_data/normalize_chicago_to_canonical.py`

Configurable path:
- `scripts/load_kafka_to_postgres.py` validates `trip_completed` events and supports:
  - `CONTRACT_VALIDATION_MODE=warn` (default)
  - `CONTRACT_VALIDATION_MODE=enforce` (fails pipeline on violations)

Recommended production posture:
- keep `warn` in pilot rollout
- switch to `enforce` after city/source validation stabilizes

Canonical contract file:
- `config/contracts/op_trip_events_contract_v1.json`

Validator module:
- `scripts/contract_validator.py`

Enforced paths:
- `ingestion/open_data/normalize_nyc_to_canonical.py`
- `ingestion/open_data/normalize_chicago_to_canonical.py`

Configurable path:
- `scripts/load_kafka_to_postgres.py` validates `trip_completed` events and supports:
  - `CONTRACT_VALIDATION_MODE=warn` (default)
  - `CONTRACT_VALIDATION_MODE=enforce` (fails pipeline on violations)

Recommended production posture:
- keep `warn` in pilot rollout
- switch to `enforce` after city/source validation stabilizes
