"""
TC-02: Surge pricing activates during peak demand.

Publishes:
  - 1 surge_activated signal to rh.pricing.surge.signals.v1
  - 6 trip lifecycle events with surge_multiplier=1.8 for TC02-TRIP-001 to rh.trip.lifecycle.events.v1

City: CHI (Chicago), Friday evening rush hour, hour_of_day=18
surge_multiplier=1.8, base_fare=14.00, surged_fare=25.20
"""
import json
from datetime import datetime, timezone
from kafka import KafkaProducer

BOOTSTRAP = "localhost:9094"
SURGE_TOPIC = "rh.pricing.surge.signals.v1"
TRIP_TOPIC = "rh.trip.lifecycle.events.v1"

# --- Surge signal event (one signal = demand spike detected) ---
SURGE_SIGNAL = {
    "event_id":          "TC02-SURGE-SIG-001",
    "event_type":        "surge_activated",
    "event_time":        "2026-06-16T17:00:00+00:00",
    "city_id":           "CHI",
    "surge_multiplier":  1.8,
    "avg_surge_multiplier": 1.8,
    "requested_trips":   120,
    "completed_trips":   98,
    "active_drivers":    45,
    "source_system":     "tc02_test_producer",
    "schema_version":    "synthetic_v1",
}

# --- Trip lifecycle events with surge applied ---
TRIP_EVENTS = [
    {
        "event_id":        "TC02-EVT-001",
        "trip_id":         "TC02-TRIP-001",
        "rider_id":        "TC02-RIDER-001",
        "driver_id":       "TC02-DRIVER-001",
        "vehicle_id":      "TC02-VEH-001",
        "city_id":         "CHI",
        "event_type":      "ride_requested",
        "event_time":      "2026-06-16T17:00:00+00:00",
        "fare_total":      None,
        "surge_multiplier": 1.8,
        "promotion_amount": 0.0,
        "platform_fee":    None,
        "driver_payout":   None,
        "payment_method_code": "card",
        "source_system":   "tc02_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC02-EVT-002",
        "trip_id":         "TC02-TRIP-001",
        "rider_id":        "TC02-RIDER-001",
        "driver_id":       "TC02-DRIVER-001",
        "vehicle_id":      "TC02-VEH-001",
        "city_id":         "CHI",
        "event_type":      "driver_assigned",
        "event_time":      "2026-06-16T17:01:30+00:00",
        "fare_total":      None,
        "surge_multiplier": 1.8,
        "promotion_amount": 0.0,
        "platform_fee":    None,
        "driver_payout":   None,
        "payment_method_code": "card",
        "source_system":   "tc02_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC02-EVT-003",
        "trip_id":         "TC02-TRIP-001",
        "rider_id":        "TC02-RIDER-001",
        "driver_id":       "TC02-DRIVER-001",
        "vehicle_id":      "TC02-VEH-001",
        "city_id":         "CHI",
        "event_type":      "trip_started",
        "event_time":      "2026-06-16T17:03:00+00:00",
        "fare_total":      None,
        "surge_multiplier": 1.8,
        "promotion_amount": 0.0,
        "platform_fee":    None,
        "driver_payout":   None,
        "payment_method_code": "card",
        "source_system":   "tc02_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC02-EVT-004",
        "trip_id":         "TC02-TRIP-001",
        "rider_id":        "TC02-RIDER-001",
        "driver_id":       "TC02-DRIVER-001",
        "vehicle_id":      "TC02-VEH-001",
        "city_id":         "CHI",
        "event_type":      "trip_completed",
        "event_time":      "2026-06-16T17:24:00+00:00",
        "fare_total":      25.20,
        "surge_multiplier": 1.8,
        "promotion_amount": 0.0,
        "platform_fee":    6.30,
        "driver_payout":   18.90,
        "payment_method_code": "card",
        "source_system":   "tc02_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC02-EVT-005",
        "trip_id":         "TC02-TRIP-001",
        "rider_id":        "TC02-RIDER-001",
        "driver_id":       "TC02-DRIVER-001",
        "vehicle_id":      "TC02-VEH-001",
        "city_id":         "CHI",
        "event_type":      "payment_captured",
        "event_time":      "2026-06-16T17:24:45+00:00",
        "fare_total":      25.20,
        "surge_multiplier": 1.8,
        "promotion_amount": 0.0,
        "platform_fee":    6.30,
        "driver_payout":   18.90,
        "payment_method_code": "card",
        "source_system":   "tc02_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC02-EVT-006",
        "trip_id":         "TC02-TRIP-001",
        "rider_id":        "TC02-RIDER-001",
        "driver_id":       "TC02-DRIVER-001",
        "vehicle_id":      "TC02-VEH-001",
        "city_id":         "CHI",
        "event_type":      "review_submitted",
        "event_time":      "2026-06-16T17:26:00+00:00",
        "fare_total":      25.20,
        "surge_multiplier": 1.8,
        "promotion_amount": 0.0,
        "platform_fee":    6.30,
        "driver_payout":   18.90,
        "rating":          4,
        "payment_method_code": "card",
        "source_system":   "tc02_test_producer",
        "schema_version":  "synthetic_v1",
    },
]


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    # Publish surge signal
    fut = producer.send(SURGE_TOPIC, key=SURGE_SIGNAL["event_id"], value=SURGE_SIGNAL)
    rec = fut.get(timeout=10)
    print(f"[SURGE SIGNAL] topic={rec.topic} partition={rec.partition} offset={rec.offset}")

    # Publish trip lifecycle events
    for ev in TRIP_EVENTS:
        fut = producer.send(TRIP_TOPIC, key=ev["event_id"], value=ev)
        rec = fut.get(timeout=10)
        print(f"[{ev['event_type']}] topic={rec.topic} partition={rec.partition} offset={rec.offset}")

    producer.flush()
    print("\nTC-02: All 7 events published successfully.")
    print(f"  Surge signal trip: CHI, surge_multiplier=1.8")
    print(f"  Trip: TC02-TRIP-001, fare_total=25.20, platform_fee=6.30, driver_payout=18.90")


if __name__ == "__main__":
    main()
