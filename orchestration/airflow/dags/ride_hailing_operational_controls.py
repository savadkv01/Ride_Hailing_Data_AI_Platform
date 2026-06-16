import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
import docker
from docker.types import Mount
import psycopg2

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

OPEN_DATA_MOUNTS = [
    Mount(
        source=os.getenv("HOST_LAKEHOUSE_PATH", "C:/D Drive/Projects/DE/Projects/Ride_hailing_data_ai_platform/lakehouse"),
        target="/app/lakehouse",
        type="bind",
    ),
]


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


def _spark_commands(action: str) -> list[str]:
    if action == "start":
        return [
            "sh -lc 'nohup spark-submit /opt/spark/jobs/bronze/bronze_kafka_to_bronze.py --config /opt/spark/jobs/config/topic_pipeline_config.json --bronze-root /opt/lakehouse/bronze/streaming --checkpoint-root /opt/spark/checkpoints/bronze > /tmp/stage7_bronze.log 2>&1 &'",
            "sh -lc 'nohup spark-submit /opt/spark/jobs/silver/silver_canonical_events.py --config /opt/spark/jobs/config/topic_pipeline_config.json --bronze-root /opt/lakehouse/bronze/streaming --silver-root /opt/lakehouse/silver --checkpoint-root /opt/spark/checkpoints/silver > /tmp/stage7_silver.log 2>&1 &'",
            "sh -lc 'nohup spark-submit /opt/spark/jobs/gold/gold_city_hourly_metrics.py --silver-root /opt/lakehouse/silver --gold-root /opt/lakehouse/gold --checkpoint-root /opt/spark/checkpoints/gold > /tmp/stage7_gold.log 2>&1 &'",
        ]
    return [
        "sh -lc 'pkill -f bronze_kafka_to_bronze.py || true'",
        "sh -lc 'pkill -f silver_canonical_events.py || true'",
        "sh -lc 'pkill -f gold_city_hourly_metrics.py || true'",
    ]


def run_spark_streaming_control(action: str, enabled: str, **context):
    pipeline_name = f"airflow_control_spark_streaming_{action}"
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

    try:
        with conn.cursor() as cur:
            _create_pipeline_run(
                cur,
                run_id=run_id,
                pipeline_name=pipeline_name,
                stage_name="spark",
                details={"enabled": enabled_flag, "action": action, "airflow_context": airflow_context},
            )
        conn.commit()

        if not enabled_flag:
            with conn.cursor() as cur:
                _finish_pipeline_run(cur, run_id=run_id, status="skipped", details={"action": action})
            conn.commit()
            return

        client = docker.from_env()
        spark_master = client.containers.get("rh-spark-master")
        command_results = []

        for command in _spark_commands(action):
            result = spark_master.exec_run(command)
            output = (result.output or b"").decode("utf-8", errors="ignore").strip()
            command_results.append(
                {
                    "command": command,
                    "exit_code": int(result.exit_code),
                    "output": output[-2000:] if output else "",
                }
            )
            if result.exit_code != 0:
                raise RuntimeError(f"Spark control command failed: {command}")

        with conn.cursor() as cur:
            _finish_pipeline_run(
                cur,
                run_id=run_id,
                status="success",
                details={"action": action, "commands": command_results},
            )
        conn.commit()
    except Exception as exc:
        with conn.cursor() as cur:
            _finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={"action": action, "error": str(exc)},
            )
        conn.commit()
        raise
    finally:
        conn.close()

with DAG(
    dag_id="ride_hailing_operational_controls",
    description="Operational controls DAG with separate mode toggles for ingestion-only, AI-only, DQ-only, and optional open-data batch ingestion.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={"owner": "platform", "retries": 1, "retry_delay": timedelta(minutes=2)},
    params={
        "run_spark_streaming_start": Param(False, type="boolean"),
        "run_spark_streaming_stop": Param(False, type="boolean"),
        "run_open_data_batch": Param(False, type="boolean"),
        "run_ingestion_only": Param(False, type="boolean"),
        "run_ai_only": Param(False, type="boolean"),
        "run_dq_only": Param(False, type="boolean"),
        "nyc_year": Param(2024, type="integer", minimum=2009, maximum=2100),
        "nyc_month": Param(1, type="integer", minimum=1, maximum=12),
        "chicago_limit": Param(200000, type="integer", minimum=1000, maximum=1000000),
        "producer_events_per_second": Param(3, type="integer", minimum=1, maximum=100),
        "producer_max_events": Param(60, type="integer", minimum=1, maximum=500000),
        "loader_max_records": Param(5000, type="integer", minimum=1, maximum=5000000),
        "rag_question": Param("What refund policy applies to service disruption?", type="string"),
    },
    tags=["ride-hailing", "operations", "controls"],
) as dag:
    spark_streaming_start = PythonOperator(
        task_id="spark_streaming_start",
        python_callable=run_spark_streaming_control,
        op_kwargs={"action": "start", "enabled": "{{ params.run_spark_streaming_start }}"},
    )

    spark_streaming_stop = PythonOperator(
        task_id="spark_streaming_stop",
        python_callable=run_spark_streaming_control,
        op_kwargs={"action": "stop", "enabled": "{{ params.run_spark_streaming_stop }}"},
        trigger_rule="all_done",
    )

    open_data_batch = DockerOperator(
        task_id="open_data_batch",
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
            "airflow_control_open_data_batch",
            "--enabled",
            "{{ params.run_open_data_batch }}",
            "--",
            "python",
            "scripts/run_open_data_batch.py",
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

    ingestion_publish = DockerOperator(
        task_id="ingestion_publish",
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
            "airflow_control_ingestion_publish",
            "--enabled",
            "{{ params.run_ingestion_only }}",
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

    ingestion_load = DockerOperator(
        task_id="ingestion_load",
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
            "airflow_control_ingestion_load",
            "--enabled",
            "{{ params.run_ingestion_only }}",
            "--",
            "python",
            "scripts/load_kafka_to_postgres.py",
        ],
    )

    ai_vector = DockerOperator(
        task_id="ai_vector",
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
            "airflow_control_ai_vector",
            "--enabled",
            "{{ params.run_ai_only }}",
            "--",
            "python",
            "vector/pipeline/build_and_index_vectors.py",
        ],
    )

    ai_rag = DockerOperator(
        task_id="ai_rag",
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
            "airflow_control_ai_rag",
            "--enabled",
            "{{ params.run_ai_only }}",
            "--",
            "python",
            "rag/assistant/ride_intelligence_assistant.py",
            "--question",
            "{{ params.rag_question }}",
            "--pretty",
        ],
    )

    dq_only = DockerOperator(
        task_id="dq_only",
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
            "airflow_control_dq",
            "--enabled",
            "{{ params.run_dq_only }}",
            "--",
            "python",
            "scripts/monitor_data_quality.py",
        ],
    )

    spark_streaming_start >> open_data_batch >> ingestion_publish >> ingestion_load
    ai_vector >> ai_rag
    [ingestion_load, ai_rag, dq_only] >> spark_streaming_stop
