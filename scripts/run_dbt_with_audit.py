import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import psycopg2

from env_loader import auto_load_env, postgres_connection_kwargs
from pipeline_audit import create_pipeline_run, finish_pipeline_run

auto_load_env()


def get_conn():
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    return psycopg2.connect(**postgres_connection_kwargs())


def parse_args():
    parser = argparse.ArgumentParser(description="Run dbt with pipeline run audit logging")
    parser.add_argument("--project-dir", default="warehouse/dbt")
    parser.add_argument("--profiles-dir", default=None)
    parser.add_argument("--skip-test", action="store_true")
    return parser.parse_args()


def summarize_run_results(project_dir: Path):
    run_results_path = project_dir / "target" / "run_results.json"
    if not run_results_path.exists():
        return {"run_results_found": False}

    with run_results_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    results = payload.get("results", [])
    status_counts = {}
    resource_counts = {}

    for entry in results:
        status = entry.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        unique_id = entry.get("unique_id", "")
        resource_type = unique_id.split(".", 1)[0] if "." in unique_id else "unknown"
        resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

    return {
        "run_results_found": True,
        "result_count": len(results),
        "status_counts": status_counts,
        "resource_counts": resource_counts,
    }


def run_dbt_command(command_args, cwd: Path):
    started = time.perf_counter()
    completed = subprocess.run(command_args, cwd=str(cwd), check=False)
    return {
        "command": " ".join(command_args),
        "exit_code": int(completed.returncode),
        "duration_seconds": round(time.perf_counter() - started, 3),
    }


def main():
    args = parse_args()
    run_id = f"dbt-{uuid.uuid4()}"
    run_started = time.perf_counter()

    dbt_executable = shutil.which("dbt")

    project_dir = Path(args.project_dir).resolve()

    conn = get_conn()
    conn.autocommit = False

    with conn.cursor() as cur:
        create_pipeline_run(
            cur,
            run_id=run_id,
            pipeline_name="dbt_warehouse_build",
            stage_name="dbt",
            details={
                "project_dir": str(project_dir),
                "skip_test": bool(args.skip_test),
                "dbt_executable_found": bool(dbt_executable),
            },
        )
    conn.commit()

    if not dbt_executable:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                    "error": "dbt executable not found in PATH",
                },
            )
        conn.commit()
        conn.close()
        raise SystemExit("dbt executable not found in PATH")

    command_summaries = []

    try:
        run_cmd = [dbt_executable, "run"]
        if args.profiles_dir:
            run_cmd.extend(["--profiles-dir", args.profiles_dir])
        command_summaries.append(run_dbt_command(run_cmd, project_dir))

        if not args.skip_test:
            test_cmd = [dbt_executable, "test"]
            if args.profiles_dir:
                test_cmd.extend(["--profiles-dir", args.profiles_dir])
            command_summaries.append(run_dbt_command(test_cmd, project_dir))

        all_success = all(item["exit_code"] == 0 for item in command_summaries)
        status = "success" if all_success else "failed"

        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status=status,
                details={
                    "commands": command_summaries,
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                    "run_results": summarize_run_results(project_dir),
                },
            )
        conn.commit()

        if not all_success:
            raise SystemExit(1)

        print(json.dumps({"run_id": run_id, "status": status, "commands": command_summaries}))
    except Exception as exc:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={
                    "commands": command_summaries,
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                    "error": str(exc),
                },
            )
        conn.commit()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
