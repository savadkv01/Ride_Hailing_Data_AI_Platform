"""
TC-03: Fraudulent trip payment is detected and flagged (ghost trip).

Publishes:
  - 2 trip events (trip_completed + payment_captured) for a ghost trip
    with fraud characteristics: high fare, very short distance, off-peak time,
    first-time card, fraud_score=0.92
  - 1 fraud signal event to rh.fraud.signals.v1

Ghost trip: TC03-TRIP-FRAUD-001 | city=NYC | driver=TC03-DRIVER-FRAUD-001
fare=95.00 (abnormally high), trip_distance_km=0.3, fraud_score=0.92
"""
import json
from kafka import KafkaProducer

BOOTSTRAP = "localhost:9094"
FRAUD_TOPIC = "rh.fraud.signals.v1"
TRIP_TOPIC  = "rh.trip.lifecycle.events.v1"

TRIP_EVENTS = [
    {
        "event_id":        "TC03-EVT-001B",
        "fraud_case_id":   "TC03-FRAUD-CASE-001",
        "trip_id":         "TC03-TRIP-FRAUD-001",
        "rider_id":        "TC03-RIDER-001",
        "driver_id":       "TC03-DRIVER-FRAUD-001",
        "vehicle_id":      "TC03-VEH-001",
        "city_id":         "NYC",
        "event_type":      "trip_completed",
        "event_time":      "2026-06-16T17:30:00+00:00",
        "fare_total":      95.00,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee":    23.75,
        "driver_payout":   71.25,
        "fraud_score":     0.92,
        "payment_method_code": "new_card",
        "source_system":   "tc03_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC03-EVT-002B",
        "fraud_case_id":   "TC03-FRAUD-CASE-001",
        "trip_id":         "TC03-TRIP-FRAUD-001",
        "rider_id":        "TC03-RIDER-001",
        "driver_id":       "TC03-DRIVER-FRAUD-001",
        "vehicle_id":      "TC03-VEH-001",
        "city_id":         "NYC",
        "event_type":      "payment_captured",
        "event_time":      "2026-06-16T17:30:45+00:00",
        "fare_total":      95.00,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee":    23.75,
        "driver_payout":   71.25,
        "fraud_score":     0.92,
        "payment_method_code": "new_card",
        "source_system":   "tc03_test_producer",
        "schema_version":  "synthetic_v1",
    },
]

FRAUD_SIGNAL = {
    "event_id":        "TC03-FRAUD-SIG-001B",
    "fraud_case_id":   "TC03-FRAUD-CASE-001",
    "event_type":      "fraud_signal",
    "event_time":      "2026-06-16T17:31:00+00:00",
    "trip_id":         "TC03-TRIP-FRAUD-001",
    "rider_id":        "TC03-RIDER-001",
    "driver_id":       "TC03-DRIVER-FRAUD-001",
    "city_id":         "NYC",
    "fraud_score":     0.92,
    "fare_total":      95.00,
    "surge_multiplier": 1.0,
    "source_system":   "tc03_test_producer",
    "schema_version":  "synthetic_v1",
}


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    # Publish trip events
    for ev in TRIP_EVENTS:
        fut = producer.send(TRIP_TOPIC, key=ev["event_id"], value=ev)
        rec = fut.get(timeout=10)
        print(f"[{ev['event_type']}] topic={rec.topic} partition={rec.partition} offset={rec.offset}")

    # Publish fraud signal
    fut = producer.send(FRAUD_TOPIC, key=FRAUD_SIGNAL["event_id"], value=FRAUD_SIGNAL)
    rec = fut.get(timeout=10)
    print(f"[FRAUD SIGNAL] topic={rec.topic} partition={rec.partition} offset={rec.offset}")

    producer.flush()
    print("\nTC-03: All 3 events published successfully.")
    print("  Ghost trip: TC03-TRIP-FRAUD-001 | fare=95.00 | fraud_score=0.92 | city=NYC | event_time=17:30 UTC")


if __name__ == "__main__":
    main()
