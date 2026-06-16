import json
import os
import uuid
from datetime import datetime
import time

from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import execute_batch
from env_loader import auto_load_env, postgres_connection_kwargs
from pipeline_audit import create_pipeline_run, finish_pipeline_run
from contract_validator import validate_records

auto_load_env()

TOPICS = [
    "rh.trip.lifecycle.events.v1",
    "rh.driver.location.pings.v1",
    "rh.rider.app.events.v1",
    "rh.payment.transactions.v1",
    "rh.pricing.surge.signals.v1",
    "rh.promotion.events.v1",
    "rh.refund.events.v1",
    "rh.review.events.v1",
    "rh.earnings.events.v1",
    "rh.incentive.events.v1",
    "rh.fraud.signals.v1",
    "rh.support.tickets.v1",
    "rh.geo.events.v1",
    "rh.city.agg.events.v1",
    "rh.revenue.margin.events.v1",
]


def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_event_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def row_from_payload(payload):
    return (
        payload.get("event_id"),
        payload.get("event_type"),
        parse_event_time(payload.get("event_time")),
        payload.get("city_id"),
        payload.get("trip_id"),
        payload.get("rider_id"),
        payload.get("driver_id"),
        payload.get("vehicle_id"),
        payload.get("payment_id"),
        payload.get("refund_id"),
        payload.get("review_id"),
        payload.get("support_ticket_id"),
        payload.get("fraud_case_id"),
        to_float(payload.get("fare_total")),
        to_float(payload.get("surge_multiplier")),
        to_float(payload.get("promotion_amount")),
        to_float(payload.get("platform_fee")),
        to_float(payload.get("driver_payout")),
        to_float(payload.get("payment_amount") or payload.get("amount")),
        to_float(payload.get("refund_amount")),
        to_float(payload.get("rating_value")),
        to_float(payload.get("fraud_score")),
        to_float(payload.get("latitude")),
        to_float(payload.get("longitude")),
        to_float(payload.get("avg_surge_multiplier")),
        to_int(payload.get("requested_trips")),
        to_int(payload.get("completed_trips")),
        to_int(payload.get("active_drivers")),
        payload.get("source_system"),
        payload.get("schema_version"),
    )


def main():
    run_started = time.perf_counter()
    run_id = f"ingest-{uuid.uuid4()}"
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
    max_records = int(os.getenv("MAX_RECORDS", "5000"))
    contract_validation_mode = os.getenv("CONTRACT_VALIDATION_MODE", "warn").strip().lower()
    contract_file = os.getenv("CONTRACT_FILE", "config/contracts/op_trip_events_contract_v1.json")

    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=bootstrap,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id=f"warehouse-loader-{uuid.uuid4()}",
        consumer_timeout_ms=8000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    records = []
    payloads = []
    seen_event_ids = set()

    for message in consumer:
        payload = message.value
        if not isinstance(payload, dict):
            continue
        event_id = payload.get("event_id")
        if not event_id or event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)
        payloads.append(payload)
        records.append(row_from_payload(payload))
        if len(records) >= max_records:
            break

    consumer.close()

    conn = psycopg2.connect(**postgres_connection_kwargs())
    conn.autocommit = False

    trip_completed_payloads = [
        payload
        for payload in payloads
        if payload.get("event_type") == "trip_completed" and payload.get("trip_id")
    ]
    contract_validation = {
        "mode": contract_validation_mode,
        "validated_records": len(trip_completed_payloads),
        "valid": True,
        "error_count": 0,
        "errors": [],
    }

    if trip_completed_payloads:
        contract_validation = validate_records(trip_completed_payloads, contract_file=contract_file)
        contract_validation["mode"] = contract_validation_mode
        contract_validation["validated_records"] = len(trip_completed_payloads)
        if not contract_validation["valid"] and contract_validation_mode == "enforce":
            raise ValueError(f"Contract validation failed: {contract_validation['errors']}")

    with conn.cursor() as cur:
        create_pipeline_run(
            cur,
            run_id=run_id,
            pipeline_name="kafka_to_postgres_loader",
            stage_name="ingestion",
            details={"max_records": max_records, "kafka_bootstrap": bootstrap},
        )
    conn.commit()

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

    try:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            cur.execute("truncate table staging.silver_canonical_events")
            if records:
                execute_batch(cur, insert_sql, records, page_size=500)

            finish_pipeline_run(
                cur,
                run_id=run_id,
                status="success",
                details={
                    "records_processed": len(records),
                    "contract_validation": contract_validation,
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
                    "records_processed": len(records),
                    "duration_seconds": round(time.perf_counter() - run_started, 3),
                    "error": str(exc),
                },
            )
        conn.commit()
        conn.close()
        raise

    conn.close()

    print(f"run_id={run_id} loaded_records={len(records)}")


if __name__ == "__main__":
    main()
