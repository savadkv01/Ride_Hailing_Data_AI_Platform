# Docker Compose Runbook

## Prerequisites
- Docker Desktop (Linux containers + WSL2 integration enabled)
- VS Code terminal at repository root

## Environment files
- `.env.local` for normal local development
- `.env.enterprise-sim` for high-load simulation profile

Python pipelines and utility scripts also auto-load env files (default search includes `docker/compose/.env.local`).
You can override explicitly with:
- `ENV_FILE=path/to/.env`

## Start commands (from repository root)

### 1) Core services only
```powershell
docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml up -d
```

### 2) Core + Spark
```powershell
docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.spark.yml up -d
```

### 3) Core + Spark + Monitoring
```powershell
docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.spark.yml -f docker/compose/docker-compose.monitoring.yml up -d
```

### 4) Full with Airflow (optional)
```powershell
docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.spark.yml -f docker/compose/docker-compose.monitoring.yml -f docker/compose/docker-compose.airflow.yml up -d
```

### 5) Build containerized job images (for Airflow DockerOperator)
```powershell
docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.jobs.yml build ingestion-jobs warehouse-jobs ml-jobs ai-jobs
```

## Stop commands
```powershell
docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.spark.yml -f docker/compose/docker-compose.monitoring.yml -f docker/compose/docker-compose.airflow.yml down
```

## Health endpoints
- FastAPI: http://localhost:8000/health
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Weaviate: http://localhost:8080/v1/.well-known/ready
- Spark UI: http://localhost:8081
- Airflow UI: http://localhost:8088

## Airflow containerized orchestration
- DAG location: `orchestration/airflow/dags/ride_hailing_e2e_orchestrator.py`
- DAG ID: `ride_hailing_e2e_orchestrator`
- Additional controls DAG location: `orchestration/airflow/dags/ride_hailing_operational_controls.py`
- Controls DAG ID: `ride_hailing_operational_controls`
- Trigger from Airflow UI and control which stages run via params:
	- `run_ingestion`, `run_stage7_spark_once`, `run_direct_kafka_loader`, `run_dbt`, `run_ml`, `run_vector`, `run_rag`, `run_dq`
	- optional open-data batch: `run_open_data_batch`, `nyc_year`, `nyc_month`, `chicago_limit`
	- `producer_events_per_second`, `producer_max_events`, `loader_max_records`, `rag_question`

### E2E ingestion convergence mode
- Default path (recommended):
	1) Synthetic Kafka publish
	2) Spark Stage 7 trigger-once pipeline (Bronze -> Silver -> Gold)
	3) `scripts/load_spark_silver_to_postgres.py` loads Spark Silver canonical events into `staging.silver_canonical_events`
	4) dbt models consume staging source and build dimensions/facts/marts
- Fallback path: set `run_direct_kafka_loader=true` to use `scripts/load_kafka_to_postgres.py` directly.

### Spark in Airflow controls
- Spark Stage 7 jobs are continuous streams and are managed as start/stop controls in `ride_hailing_operational_controls`:
	- `run_spark_streaming_start`: starts Bronze, Silver, and Gold Spark streaming jobs in `rh-spark-master`
	- `run_spark_streaming_stop`: stops Spark streaming jobs by process match
- Spark control runs are audit-logged to `metadata.pipeline_run_audit` with pipeline names:
	- `airflow_control_spark_streaming_start`
	- `airflow_control_spark_streaming_stop`

### Where NYC/Chicago batch ingestion is included
- Script: `scripts/run_open_data_batch.py`
- E2E DAG task: `open_data_batch_ingestion` (optional via `run_open_data_batch`)
- Controls DAG task: `open_data_batch` (optional via `run_open_data_batch`)
- Outputs:
	- `lakehouse/bronze/open/nyc_tlc/yellow_tripdata_<year>-<month>.parquet`
	- `lakehouse/bronze/open/chicago_taxi/chicago_taxi_trips.csv`
	- `lakehouse/bronze/canonical/op_trip_events_nyc_<year>_<month>.parquet`
	- `lakehouse/bronze/canonical/op_trip_events_chicago_sample.parquet`

## Logging and run audit through Airflow
- Airflow task logs are persisted under `logs/airflow` via compose volume mounts.
- Every Airflow-triggered container task runs through `scripts/airflow_task_runner.py`.
- This writes stage lifecycle rows to `metadata.pipeline_run_audit` with:
	- run status (`running`/`success`/`failed`/`skipped`)
	- command details and return code
	- Airflow context (`AIRFLOW_CTX_DAG_ID`, `AIRFLOW_CTX_TASK_ID`, `AIRFLOW_CTX_RUN_ID`, etc.)

## Kafka topic bootstrap
After Kafka starts, run topic bootstrap in the Kafka container:
```powershell
docker exec -it rh-kafka bash -c "/bin/bash /opt/kafka/topics-bootstrap.sh"
```
