import os
import uuid
from datetime import datetime, timedelta, timezone
import time

import psycopg2
from env_loader import auto_load_env, postgres_connection_kwargs
from pipeline_audit import create_pipeline_run, finish_pipeline_run

auto_load_env()


def get_conn():
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    return psycopg2.connect(**postgres_connection_kwargs())


def ensure_audit_table(cur):
    cur.execute("create schema if not exists metadata")
    cur.execute(
        """
        create table if not exists metadata.data_quality_audit (
            audit_id bigserial primary key,
            run_id text not null,
            rule_id text not null,
            target_entity text not null,
            status text not null,
            violation_count bigint default 0,
            observed_at timestamp not null default current_timestamp
        )
        """
    )


def check_kpi_not_empty(cur):
    cur.execute("select count(*) from gold.mart_city_daily_kpis")
    row_count = int(cur.fetchone()[0])
    violations = 0 if row_count > 0 else 1
    return "kpi_table_not_empty", "gold.mart_city_daily_kpis", violations


def check_kpi_freshness(cur, freshness_days):
    cur.execute("select max(event_date) from gold.mart_city_daily_kpis")
    max_event_date = cur.fetchone()[0]
    if max_event_date is None:
        return "kpi_table_freshness", "gold.mart_city_daily_kpis", 1

    threshold = (datetime.now(timezone.utc).date() - timedelta(days=freshness_days))
    violations = 0 if max_event_date >= threshold else 1
    return "kpi_table_freshness", "gold.mart_city_daily_kpis", violations


def check_negative_fares(cur):
    cur.execute("select count(*) from gold.mart_city_daily_kpis where gross_fare_total < 0")
    violations = int(cur.fetchone()[0])
    return "kpi_negative_fares", "gold.mart_city_daily_kpis", violations


def write_audit(cur, run_id, rule_id, target_entity, violations):
    status = "passed" if violations == 0 else "failed"
    cur.execute(
        """
        insert into metadata.data_quality_audit (
            run_id, rule_id, target_entity, status, violation_count, observed_at
        ) values (%s, %s, %s, %s, %s, current_timestamp)
        """,
        (run_id, rule_id, target_entity, status, violations),
    )
    return status


def main():
    run_started = time.perf_counter()
    freshness_days = int(os.getenv("DQ_FRESHNESS_MAX_DAYS", "1"))
    run_id = f"dq-{uuid.uuid4()}"

    checks = [
        check_kpi_not_empty,
        lambda cur: check_kpi_freshness(cur, freshness_days),
        check_negative_fares,
    ]

    conn = get_conn()
    conn.autocommit = False

    failed_checks = 0

    with conn.cursor() as cur:
        create_pipeline_run(
            cur,
            run_id=run_id,
            pipeline_name="data_quality_monitor",
            stage_name="quality",
            details={"freshness_max_days": freshness_days, "total_checks": len(checks)},
        )
    conn.commit()

    try:
        with conn.cursor() as cur:
            ensure_audit_table(cur)

            for check_fn in checks:
                rule_id, target_entity, violations = check_fn(cur)
                status = write_audit(cur, run_id, rule_id, target_entity, violations)
                if status == "failed":
                    failed_checks += 1
                print(
                    f"run_id={run_id} rule_id={rule_id} target={target_entity} "
                    f"status={status} violations={violations}"
                )

            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="success" if failed_checks == 0 else "failed",
                details={
                    "failed_checks": failed_checks,
                    "passed_checks": len(checks) - failed_checks,
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                },
            )

        conn.commit()
    except Exception as exc:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={
                    "failed_checks": failed_checks,
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                    "error": str(exc),
                },
            )
        conn.commit()
        conn.close()
        raise

    conn.close()

    print(f"run_id={run_id} total_checks={len(checks)} failed_checks={failed_checks}")
    if failed_checks > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
