import argparse
import json
import os
import subprocess
import time
import uuid

import psycopg2

from env_loader import auto_load_env, postgres_connection_kwargs
from pipeline_audit import create_pipeline_run, finish_pipeline_run


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command with pipeline audit logging and Airflow context.")
    parser.add_argument("--pipeline-name", required=True)
    parser.add_argument("--stage-name", default="airflow")
    parser.add_argument("--enabled", default="true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def get_airflow_context() -> dict:
    keys = [
        "AIRFLOW_CTX_DAG_ID",
        "AIRFLOW_CTX_TASK_ID",
        "AIRFLOW_CTX_RUN_ID",
        "AIRFLOW_CTX_TRY_NUMBER",
        "AIRFLOW_CTX_EXECUTION_DATE",
    ]
    context = {}
    for key in keys:
        value = os.getenv(key)
        if value:
            context[key] = value
    return context


def main() -> None:
    args = parse_args()
    auto_load_env()

    enabled = parse_bool(args.enabled)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]

    run_id = f"airflow-{args.pipeline_name}-{uuid.uuid4()}"
    started = time.perf_counter()

    conn = psycopg2.connect(**postgres_connection_kwargs())
    conn.autocommit = False

    initial_details = {
        "enabled": enabled,
        "airflow_context": get_airflow_context(),
        "command": command,
    }

    with conn.cursor() as cur:
        create_pipeline_run(
            cur,
            run_id=run_id,
            pipeline_name=args.pipeline_name,
            stage_name=args.stage_name,
            details=initial_details,
        )
    conn.commit()

    if not enabled:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="skipped",
                details={"duration_seconds": round(time.perf_counter() - started, 3)},
            )
        conn.commit()
        conn.close()
        print(json.dumps({"run_id": run_id, "status": "skipped", "pipeline_name": args.pipeline_name}))
        return

    if not command:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={
                    "duration_seconds": round(time.perf_counter() - started, 3),
                    "error": "No command provided",
                },
            )
        conn.commit()
        conn.close()
        raise SystemExit("No command provided")

    try:
        completed = subprocess.run(command, check=False)
        status = "success" if completed.returncode == 0 else "failed"
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status=status,
                details={
                    "duration_seconds": round(time.perf_counter() - started, 3),
                    "return_code": int(completed.returncode),
                },
            )
        conn.commit()

        result = {
            "run_id": run_id,
            "status": status,
            "pipeline_name": args.pipeline_name,
            "return_code": int(completed.returncode),
        }
        print(json.dumps(result))

        if completed.returncode != 0:
            raise SystemExit(int(completed.returncode))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
