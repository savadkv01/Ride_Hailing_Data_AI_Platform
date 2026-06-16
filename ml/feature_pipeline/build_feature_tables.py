import os
import sys
import time
import uuid
from pathlib import Path
import psycopg2


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.pipeline_audit import create_pipeline_run, finish_pipeline_run
from scripts.env_loader import auto_load_env, postgres_connection_kwargs

auto_load_env(project_root=PROJECT_ROOT)


def get_conn():
    return psycopg2.connect(**postgres_connection_kwargs())


def main():
    run_started = time.perf_counter()
    run_id = f"ml-feature-{uuid.uuid4()}"
    sql = """
    create schema if not exists ml;

    drop table if exists ml.feature_demand_city_daily;
    create table ml.feature_demand_city_daily as
    select
        event_date,
        city_id,
        completed_trips,
        cancelled_trips,
        gross_fare_total,
        platform_fee_total,
        driver_payout_total,
        avg_surge_multiplier
    from gold.mart_city_daily_kpis;

    drop table if exists ml.feature_fraud_trip;
    create table ml.feature_fraud_trip as
    select
        f.fraud_fact_key,
        f.trip_id,
        f.city_key,
        f.fraud_score,
        case when f.risk_band = 'high' then 1 else 0 end as is_high_risk,
        coalesce(t.final_fare, 0) as final_fare,
        coalesce(t.surge_multiplier, 1) as surge_multiplier,
        coalesce(t.cancelled_flag, 0) as cancelled_flag,
        coalesce(t.completed_flag, 0) as completed_flag
    from gold.fact_fraud f
    left join gold.fact_trip t on t.trip_id = f.trip_id;

    drop table if exists ml.feature_rider_churn_daily;
    create table ml.feature_rider_churn_daily as
    with rider_activity as (
        select
            rider_key,
            cast(created_at as date) as activity_date,
            count(*) as trip_events,
            max(cast(created_at as date)) over (partition by rider_key) as last_activity_date
        from gold.fact_trip
        group by rider_key, cast(created_at as date)
    )
    select
        rider_key,
        activity_date,
        trip_events,
        case when last_activity_date <= activity_date + interval '7 day' then 0 else 1 end as churned_7d
    from rider_activity;
    """

    conn = get_conn()
    conn.autocommit = False

    with conn.cursor() as cur:
        create_pipeline_run(
            cur,
            run_id=run_id,
            pipeline_name="ml_feature_table_builder",
            stage_name="ml_feature",
            details={"target_schema": "ml", "target_tables": 3},
        )
    conn.commit()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)

            with conn.cursor() as cur:
                finish_pipeline_run(
                    cur,
                    run_id=run_id,
                    status="success",
                    details={
                        "target_schema": "ml",
                        "target_tables": 3,
                        "duration_seconds": round(time.perf_counter() - run_started, 3),
                    },
                )
        print(f"run_id={run_id} feature tables built in schema ml")
    except Exception as exc:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="failed",
                details={
                    "target_schema": "ml",
                    "target_tables": 3,
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                    "error": str(exc),
                },
            )
        conn.commit()
        conn.close()
        raise

    conn.close()


if __name__ == "__main__":
    main()
