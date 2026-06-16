import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
import docker
from docker.types import Mount
import psycopg2

try:
    import yaml
except ImportError:
    yaml = None

COMMON_ENV = {
    "ENV_FILE": "docker/compose/.env.local",
    "POSTGRES_HOST": "postgres",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "ride_warehouse",
    "POSTGRES_USER": "ride_admin",
    "POSTGRES_PASSWORD": "ride_password",
    "KAFKA_BOOTSTRAP": "kafka:9092",
    "WEAVIATE_URL": "http://weaviate:8080",
    "OLLAMA_URL": "http://ollama:11434",
}

HOST_PROJECT_ROOT = os.getenv("HOST_PROJECT_ROOT", "C:/D Drive/Projects/DE/Projects/Ride_hailing_data_ai_platform")
HOST_LAKEHOUSE_PATH = os.getenv("HOST_LAKEHOUSE_PATH", f"{HOST_PROJECT_ROOT}/lakehouse")

OPEN_DATA_MOUNTS = [
    Mount(source=HOST_LAKEHOUSE_PATH, target="/app/lakehouse", type="bind"),
]


def _load_enabled_open_data_cities() -> list[str]:
    default_cities = ["NYC", "CHICAGO"]
    if yaml is None:
        return default_cities

    config_path = Path(HOST_PROJECT_ROOT) / "config" / "scaling" / "multi_city_expansion.yaml"
    if not config_path.exists():
        return default_cities

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    cities = []
    for city in config.get("city_registry", []):
        if not city.get("enabled", False):
            continue
        open_data_source = (city.get("data_sources") or {}).get("open_data")
        city_id = str(city.get("city_id", "")).upper()
        if open_data_source in {"nyc_tlc", "chicago_taxi"} and city_id in {"NYC", "CHICAGO"}:
            cities.append(city_id)

    return cities or default_cities


OPEN_DATA_ENABLED_CITIES = _load_enabled_open_data_cities()


def _parse_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_conn():
    return psycopg2.connect(
        host=COMMON_ENV["POSTGRES_HOST"],
        port=COMMON_ENV["POSTGRES_PORT"],
        dbname=COMMON_ENV["POSTGRES_DB"],
        user=COMMON_ENV["POSTGRES_USER"],
        password=COMMON_ENV["POSTGRES_PASSWORD"],
    )


def _ensure_pipeline_run_audit_table(cur):
    cur.execute("create schema if not exists metadata")
    cur.execute(
        """
        create table if not exists metadata.pipeline_run_audit (
            run_id text primary key,
            pipeline_name text not null,
            stage_name text not null,
            status text not null,
            started_at timestamp not null default current_timestamp,
            ended_at timestamp,
            details jsonb
        )
        """
    )


def _create_pipeline_run(cur, run_id, pipeline_name, stage_name, details=None):
    _ensure_pipeline_run_audit_table(cur)
    cur.execute(
        """
        insert into metadata.pipeline_run_audit (
            run_id, pipeline_name, stage_name, status, started_at, details
        ) values (%s, %s, %s, %s, %s, %s::jsonb)
        on conflict (run_id) do update
        set pipeline_name = excluded.pipeline_name,
            stage_name = excluded.stage_name,
            status = excluded.status,
            started_at = excluded.started_at,
            ended_at = null,
            details = excluded.details
        """,
        (run_id, pipeline_name, stage_name, "running", _utc_now_naive(), json.dumps(details or {})),
    )


def _finish_pipeline_run(cur, run_id, status, details=None):
    cur.execute(
        """
        update metadata.pipeline_run_audit
        set
            status = %s,
            ended_at = %s,
            details = coalesce(details, '{}'::jsonb) || (%s::jsonb)
        where run_id = %s
        """,
        (status, _utc_now_naive(), json.dumps(details or {}), run_id),
    )


def run_spark_stage7_once(enabled: str, **context):
    pipeline_name = "airflow_spark_stage7_once"
    run_id = f"airflow-{pipeline_name}-{uuid.uuid4()}"
    enabled_flag = _parse_bool(enabled)

    airflow_context = {
        "AIRFLOW_CTX_DAG_ID": context.get("dag").dag_id if context.get("dag") else None,
        "AIRFLOW_CTX_TASK_ID": context.get("task").task_id if context.get("task") else None,
        "AIRFLOW_CTX_RUN_ID": context.get("run_id"),
        "AIRFLOW_CTX_EXECUTION_DATE": str(context.get("logical_date")) if context.get("logical_date") else None,
    }
    airflow_context = {k: v for k, v in airflow_context.items() if v is not None}

    conn = _get_conn()
    conn.autocommit = False

    commands = [
        "/opt/spark/bin/spark-submit /opt/spark/jobs/bronze/bronze_kafka_to_bronze.py --config /opt/spark/jobs/config/topic_pipeline_config.json --bronze-root /opt/lakehouse/bronze/streaming --checkpoint-root /opt/spark/checkpoints/bronze --trigger-once",
        "/opt/spark/bin/spark-submit /opt/spark/jobs/silver/silver_canonical_events.py --config /opt/spark/jobs/config/topic_pipeline_config.json --bronze-root /opt/lakehouse/bronze/streaming --silver-root /opt/lakehouse/silver --checkpoint-root /opt/spark/checkpoints/silver --trigger-once",
        "/opt/spark/bin/spark-submit /opt/spark/jobs/gold/gold_city_hourly_metrics.py --silver-root /opt/lakehouse/silver --gold-root /opt/lakehouse/gold --checkpoint-root /opt/spark/checkpoints/gold --trigger-once",
    ]

    try:
        with conn.cursor() as cur:
            _create_pipeline_run(
                cur,
                run_id=run_id,
                pipeline_name=pipeline_name,
                stage_name="spark",
                details={"enabled": enabled_flag, "airflow_context": airflow_context, "mode": "trigger_once"},
            )
        conn.commit()

        if not enabled_flag:
            with conn.cursor() as cur:
                _finish_pipeline_run(cur, run_id=run_id, status="skipped", details={"mode": "trigger_once"})
            conn.commit()
            return

        client = docker.from_env()
        spark_master = client.containers.get("rh-spark-master")
        results = []

        for command in commands:
            exec_command = f"sh -lc \"{command}\""
            result = spark_master.exec_run(exec_command)
            output = (result.output or b"").decode("utf-8", errors="ignore").strip()
            results.append(
                {
                    "command": command,
                    "exit_code": int(result.exit_code),
                    "output_tail": output[-2000:] if output else "",
                }
            )
            if result.exit_code != 0:
                output_tail = output[-2000:] if output else ""
                raise RuntimeError(
                    f"Spark stage7 command failed: {command} | exit_code={result.exit_code} | output_tail={output_tail}"
                )

        with conn.cursor() as cur:
            _finish_pipeline_run(
                cur,
                run_id=run_id,
                status="success",
                details={"mode": "trigger_once", "commands": results},
            )
        conn.commit()
    except Exception as exc:
        with conn.cursor() as cur:
            _finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={"mode": "trigger_once", "error": str(exc)},
            )
        conn.commit()
        raise
    finally:
        conn.close()

with DAG(
    dag_id="ride_hailing_e2e_orchestrator",
    description="Containerized end-to-end orchestration for ingestion, warehouse, ML, vector, RAG, and quality monitoring.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={"owner": "platform", "retries": 1, "retry_delay": timedelta(minutes=2)},
    params={
        "run_ingestion": Param(True, type="boolean"),
        "run_stage7_spark_once": Param(False, type="boolean"),
        "run_direct_kafka_loader": Param(True, type="boolean"),
        "run_open_data_batch": Param(False, type="boolean"),
        "run_dbt": Param(True, type="boolean"),
        "run_ml": Param(True, type="boolean"),
        "run_vector": Param(True, type="boolean"),
        "run_rag": Param(True, type="boolean"),
        "run_dq": Param(True, type="boolean"),
        "nyc_year": Param(2024, type="integer", minimum=2009, maximum=2100),
        "nyc_month": Param(1, type="integer", minimum=1, maximum=12),
        "chicago_limit": Param(200000, type="integer", minimum=1000, maximum=1000000),
        "producer_events_per_second": Param(3, type="integer", minimum=1, maximum=100),
        "producer_max_events": Param(60, type="integer", minimum=1, maximum=500000),
        "loader_max_records": Param(5000, type="integer", minimum=1, maximum=5000000),
        "rag_question": Param("What refund policy applies to service disruption?", type="string"),
    },
    tags=["ride-hailing", "e2e", "containerized"],
) as dag:
    spark_stage7_pipeline_once = PythonOperator(
        task_id="spark_stage7_pipeline_once",
        python_callable=run_spark_stage7_once,
        op_kwargs={"enabled": "{{ params.run_stage7_spark_once and params.run_ingestion }}"},
    )

    open_data_batch_tasks = []
    for city_id in OPEN_DATA_ENABLED_CITIES:
        task = DockerOperator(
            task_id=f"open_data_batch_{city_id.lower()}",
            image="rh-ingestion-jobs:local",
            api_version="auto",
            auto_remove=True,
            docker_url="unix://var/run/docker.sock",
            network_mode="platform_core_net",
            mount_tmp_dir=False,
            environment=COMMON_ENV,
            mounts=OPEN_DATA_MOUNTS,
            command=[
                "python",
                "scripts/airflow_task_runner.py",
                "--pipeline-name",
                f"airflow_open_data_batch_{city_id.lower()}",
                "--enabled",
                "{{ params.run_open_data_batch }}",
                "--",
                "python",
                "scripts/run_open_data_city_batch.py",
                "--city-id",
                city_id,
                "--incremental",
                "--nyc-year",
                "{{ params.nyc_year }}",
                "--nyc-month",
                "{{ params.nyc_month }}",
                "--chicago-limit",
                "{{ params.chicago_limit }}",
                "--for-date",
                "{{ ds }}",
            ],
        )
        open_data_batch_tasks.append(task)

    synthetic_publish = DockerOperator(
        task_id="synthetic_publish",
        image="rh-ingestion-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_synthetic_publish",
            "--enabled",
            "{{ params.run_ingestion }}",
            "--",
            "python",
            "-m",
            "ingestion.synthetic.catalog_producer_manager",
            "--catalog-index",
            "config/source_catalog/source_catalog_index.yaml",
            "--bootstrap-servers",
            "kafka:9092",
            "--events-per-second",
            "{{ params.producer_events_per_second }}",
            "--max-events",
            "{{ params.producer_max_events }}",
        ],
    )

    kafka_to_postgres = DockerOperator(
        task_id="kafka_to_postgres",
        image="rh-ingestion-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment={**COMMON_ENV, "MAX_RECORDS": "{{ params.loader_max_records }}"},
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_kafka_to_postgres",
            "--enabled",
            "{{ 'true' if params.run_ingestion and params.run_direct_kafka_loader else 'false' }}",
            "--",
            "python",
            "scripts/load_kafka_to_postgres.py",
        ],
    )

    spark_silver_to_postgres = DockerOperator(
        task_id="spark_silver_to_postgres",
        image="rh-ingestion-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        mounts=OPEN_DATA_MOUNTS,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_spark_silver_to_postgres",
            "--enabled",
            "{{ 'true' if params.run_ingestion and (not params.run_direct_kafka_loader) else 'false' }}",
            "--",
            "python",
            "scripts/load_spark_silver_to_postgres.py",
            "--silver-root",
            "lakehouse/silver",
        ],
    )

    dbt_transform = DockerOperator(
        task_id="dbt_transform",
        image="rh-warehouse-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_dbt_transform",
            "--enabled",
            "{{ params.run_dbt }}",
            "--",
            "python",
            "scripts/run_dbt_with_audit.py",
            "--profiles-dir",
            "/app/warehouse/dbt",
        ],
    )

    ml_features = DockerOperator(
        task_id="ml_features",
        image="rh-ml-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_ml_features",
            "--enabled",
            "{{ params.run_ml }}",
            "--",
            "python",
            "ml/feature_pipeline/build_feature_tables.py",
        ],
    )

    train_demand = DockerOperator(
        task_id="train_demand",
        image="rh-ml-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_train_demand",
            "--enabled",
            "{{ params.run_ml }}",
            "--",
            "python",
            "ml/training/train_demand_model.py",
        ],
    )

    train_surge = DockerOperator(
        task_id="train_surge",
        image="rh-ml-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_train_surge",
            "--enabled",
            "{{ params.run_ml }}",
            "--",
            "python",
            "ml/training/train_surge_model.py",
        ],
    )

    train_fraud = DockerOperator(
        task_id="train_fraud",
        image="rh-ml-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_train_fraud",
            "--enabled",
            "{{ params.run_ml }}",
            "--",
            "python",
            "ml/training/train_fraud_model.py",
        ],
    )

    train_churn = DockerOperator(
        task_id="train_churn",
        image="rh-ml-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_train_churn",
            "--enabled",
            "{{ params.run_ml }}",
            "--",
            "python",
            "ml/training/train_churn_model.py",
        ],
    )

    vector_index = DockerOperator(
        task_id="vector_index",
        image="rh-ai-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_vector_index",
            "--enabled",
            "{{ params.run_vector }}",
            "--",
            "python",
            "vector/pipeline/build_and_index_vectors.py",
        ],
    )

    rag_query = DockerOperator(
        task_id="rag_query",
        image="rh-ai-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_rag_query",
            "--enabled",
            "{{ params.run_rag }}",
            "--",
            "python",
            "rag/assistant/ride_intelligence_assistant.py",
            "--question",
            "{{ params.rag_question }}",
            "--pretty",
        ],
    )

    quality_checks = DockerOperator(
        task_id="quality_checks",
        image="rh-ingestion-jobs:local",
        api_version="auto",
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="platform_core_net",
        mount_tmp_dir=False,
        environment=COMMON_ENV,
        command=[
            "python",
            "scripts/airflow_task_runner.py",
            "--pipeline-name",
            "airflow_quality_checks",
            "--enabled",
            "{{ params.run_dq }}",
            "--",
            "python",
            "scripts/monitor_data_quality.py",
        ],
    )

    for open_data_task in open_data_batch_tasks:
        open_data_task >> synthetic_publish
    synthetic_publish >> spark_stage7_pipeline_once
    spark_stage7_pipeline_once >> spark_silver_to_postgres
    synthetic_publish >> kafka_to_postgres
    [kafka_to_postgres, spark_silver_to_postgres] >> dbt_transform >> ml_features
    ml_features >> [train_demand, train_surge, train_fraud, train_churn] >> vector_index >> rag_query >> quality_checks
