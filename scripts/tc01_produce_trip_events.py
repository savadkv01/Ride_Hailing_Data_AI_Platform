"""
TC-01: Produce deterministic trip lifecycle events for test case validation.

Publishes the 6 canonical lifecycle events for trip TC01-TRIP-001 to
rh.trip.lifecycle.events.v1 with fixed, verifiable field values.
"""
import json
from datetime import datetime, timezone
from kafka import KafkaProducer

BOOTSTRAP = "localhost:9094"
TOPIC = "rh.trip.lifecycle.events.v1"

BASE_TIME = "2026-06-16T09:00:00+00:00"

EVENTS = [
    {
        "event_id":   "TC01-EVT-001",
        "trip_id":    "TC01-TRIP-001",
        "rider_id":   "TC01-RIDER-001",
        "driver_id":  "TC01-DRIVER-001",
        "vehicle_id": "TC01-VEH-001",
        "city_id":    "NYC",
        "event_type": "ride_requested",
        "event_time": "2026-06-16T09:00:00+00:00",
        "ingestion_time": datetime.now(timezone.utc).isoformat(),
        "fare_total": None,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee": None,
        "driver_payout": None,
        "payment_method_code": "card",
        "source_system": "tc01_test_producer",
        "source_record_id": "TC01-SRC-001",
        "schema_version": "synthetic_v1",
    },
    {
        "event_id":   "TC01-EVT-002",
        "trip_id":    "TC01-TRIP-001",
        "rider_id":   "TC01-RIDER-001",
        "driver_id":  "TC01-DRIVER-001",
        "vehicle_id": "TC01-VEH-001",
        "city_id":    "NYC",
        "event_type": "driver_assigned",
        "event_time": "2026-06-16T09:01:30+00:00",
        "ingestion_time": datetime.now(timezone.utc).isoformat(),
        "fare_total": None,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee": None,
        "driver_payout": None,
        "payment_method_code": "card",
        "source_system": "tc01_test_producer",
        "source_record_id": "TC01-SRC-002",
        "schema_version": "synthetic_v1",
    },
    {
        "event_id":   "TC01-EVT-003",
        "trip_id":    "TC01-TRIP-001",
        "rider_id":   "TC01-RIDER-001",
        "driver_id":  "TC01-DRIVER-001",
        "vehicle_id": "TC01-VEH-001",
        "city_id":    "NYC",
        "event_type": "trip_started",
        "event_time": "2026-06-16T09:06:00+00:00",
        "ingestion_time": datetime.now(timezone.utc).isoformat(),
        "fare_total": None,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee": None,
        "driver_payout": None,
        "payment_method_code": "card",
        "source_system": "tc01_test_producer",
        "source_record_id": "TC01-SRC-003",
        "schema_version": "synthetic_v1",
    },
    {
        "event_id":   "TC01-EVT-004",
        "trip_id":    "TC01-TRIP-001",
        "rider_id":   "TC01-RIDER-001",
        "driver_id":  "TC01-DRIVER-001",
        "vehicle_id": "TC01-VEH-001",
        "city_id":    "NYC",
        "event_type": "trip_completed",
        "event_time": "2026-06-16T09:24:00+00:00",
        "ingestion_time": datetime.now(timezone.utc).isoformat(),
        "fare_total": 21.00,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee": 5.25,
        "driver_payout": 15.75,
        "payment_method_code": "card",
        "source_system": "tc01_test_producer",
        "source_record_id": "TC01-SRC-004",
        "schema_version": "synthetic_v1",
    },
    {
        "event_id":   "TC01-EVT-005",
        "trip_id":    "TC01-TRIP-001",
        "rider_id":   "TC01-RIDER-001",
        "driver_id":  "TC01-DRIVER-001",
        "vehicle_id": "TC01-VEH-001",
        "city_id":    "NYC",
        "event_type": "payment_captured",
        "event_time": "2026-06-16T09:24:45+00:00",
        "ingestion_time": datetime.now(timezone.utc).isoformat(),
        "fare_total": 21.00,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee": 5.25,
        "driver_payout": 15.75,
        "payment_method_code": "card",
        "source_system": "tc01_test_producer",
        "source_record_id": "TC01-SRC-005",
        "schema_version": "synthetic_v1",
    },
    {
        "event_id":   "TC01-EVT-006",
        "trip_id":    "TC01-TRIP-001",
        "rider_id":   "TC01-RIDER-001",
        "driver_id":  "TC01-DRIVER-001",
        "vehicle_id": "TC01-VEH-001",
        "city_id":    "NYC",
        "event_type": "review_submitted",
        "event_time": "2026-06-16T09:26:00+00:00",
        "ingestion_time": datetime.now(timezone.utc).isoformat(),
        "fare_total": None,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee": None,
        "driver_payout": None,
        "payment_method_code": "card",
        "rating": 5,
        "source_system": "tc01_test_producer",
        "source_record_id": "TC01-SRC-006",
        "schema_version": "synthetic_v1",
    },
]


def main() -> None:
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        acks="all",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    for evt in EVENTS:
        future = producer.send(TOPIC, value=evt)
        metadata = future.get(timeout=10)
        print(
            f"[TC-01] sent {evt['event_type']:<20} "
            f"event_id={evt['event_id']}  "
            f"partition={metadata.partition}  offset={metadata.offset}"
        )

    producer.flush()
    producer.close()
    print("\n[TC-01] All 6 events published successfully.")


if __name__ == "__main__":
    main()
