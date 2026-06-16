import argparse
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

from env_loader import auto_load_env, postgres_connection_kwargs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Spark Silver canonical parquet into PostgreSQL staging table.")
    parser.add_argument("--silver-root", default="lakehouse/silver")
    parser.add_argument("--max-rows", type=int, default=0, help="Optional cap for rows loaded (0 means all)")
    return parser.parse_args()


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = [
        "event_id",
        "event_type",
        "event_time",
        "city_id",
        "trip_id",
        "rider_id",
        "driver_id",
        "vehicle_id",
        "payment_id",
        "refund_id",
        "review_id",
        "support_ticket_id",
        "fraud_case_id",
        "fare_total",
        "surge_multiplier",
        "promotion_amount",
        "platform_fee",
        "driver_payout",
        "payment_amount",
        "refund_amount",
        "rating_value",
        "fraud_score",
        "latitude",
        "longitude",
        "avg_surge_multiplier",
        "requested_trips",
        "completed_trips",
        "active_drivers",
        "source_system",
        "schema_version",
    ]

    for column in required_cols:
        if column not in df.columns:
            df[column] = None

    df = df[required_cols].copy()
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce").dt.tz_localize(None)

    numeric_float_cols = [
        "fare_total",
        "surge_multiplier",
        "promotion_amount",
        "platform_fee",
        "driver_payout",
        "payment_amount",
        "refund_amount",
        "rating_value",
        "fraud_score",
        "latitude",
        "longitude",
        "avg_surge_multiplier",
    ]
    numeric_int_cols = ["requested_trips", "completed_trips", "active_drivers"]

    for column in numeric_float_cols:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in numeric_int_cols:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    df = df.dropna(subset=["event_id", "event_time", "city_id"])
    df = df.drop_duplicates(subset=["event_id"], keep="last")

    return df


def main() -> None:
    args = parse_args()
    auto_load_env()

    canonical_path = Path(args.silver_root) / "canonical_events"
    if not canonical_path.exists():
        raise FileNotFoundError(f"Spark Silver canonical path not found: {canonical_path}")

    df = pd.read_parquet(canonical_path)
    if args.max_rows > 0:
        df = df.head(args.max_rows)

    df = normalize_dataframe(df)

    conn = psycopg2.connect(**postgres_connection_kwargs())
    conn.autocommit = False

    create_sql = """
    create schema if not exists staging;

    create table if not exists staging.silver_canonical_events (
        event_id text,
        event_type text,
        event_time timestamp,
        city_id text,
        trip_id text,
        rider_id text,
        driver_id text,
        vehicle_id text,
        payment_id text,
        refund_id text,
        review_id text,
        support_ticket_id text,
        fraud_case_id text,
        fare_total double precision,
        surge_multiplier double precision,
        promotion_amount double precision,
        platform_fee double precision,
        driver_payout double precision,
        payment_amount double precision,
        refund_amount double precision,
        rating_value double precision,
        fraud_score double precision,
        latitude double precision,
        longitude double precision,
        avg_surge_multiplier double precision,
        requested_trips bigint,
        completed_trips bigint,
        active_drivers bigint,
        source_system text,
        schema_version text
    );
    """

    insert_sql = """
    insert into staging.silver_canonical_events (
        event_id,event_type,event_time,city_id,trip_id,rider_id,driver_id,vehicle_id,
        payment_id,refund_id,review_id,support_ticket_id,fraud_case_id,fare_total,
        surge_multiplier,promotion_amount,platform_fee,driver_payout,payment_amount,
        refund_amount,rating_value,fraud_score,latitude,longitude,avg_surge_multiplier,
        requested_trips,completed_trips,active_drivers,source_system,schema_version
    ) values (
        %s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s
    )
    """

    rows = [
        tuple(None if pd.isna(value) else value for value in record)
        for record in df.itertuples(index=False, name=None)
    ]

    with conn.cursor() as cur:
        cur.execute(create_sql)
        cur.execute("truncate table staging.silver_canonical_events")
        if rows:
            execute_batch(cur, insert_sql, rows, page_size=500)
    conn.commit()
    conn.close()

    print(f"loaded_rows={len(rows)}")


if __name__ == "__main__":
    main()
