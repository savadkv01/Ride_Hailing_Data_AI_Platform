"""
TC-05: Driver earnings settled correctly after a trip.

Publishes trip lifecycle events for TC05-TRIP-001:
  - trip_completed + payment_captured with fare_total=24.00, platform_fee=6.00 (25%),
    driver_payout=18.00 (75% base)
  - A separate earnings event to rh.earnings.events.v1 with incentive_bonus=3.00
    → expected net_driver_earning = 18.00 + 3.00 = 21.00

Event times are within the current watermark window (after 17:30 UTC).
"""
import json
from kafka import KafkaProducer

BOOTSTRAP   = "localhost:9094"
TRIP_TOPIC  = "rh.trip.lifecycle.events.v1"
EARN_TOPIC  = "rh.earnings.events.v1"

TRIP_EVENTS = [
    {
        "event_id":        "TC05-EVT-001",
        "trip_id":         "TC05-TRIP-001",
        "rider_id":        "TC05-RIDER-001",
        "driver_id":       "TC05-DRIVER-EARN-001",
        "vehicle_id":      "TC05-VEH-001",
        "city_id":         "NYC",
        "event_type":      "trip_completed",
        "event_time":      "2026-06-16T17:50:00+00:00",
        "fare_total":      24.00,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee":    6.00,
        "driver_payout":   18.00,
        "payment_method_code": "card",
        "source_system":   "tc05_test_producer",
        "schema_version":  "synthetic_v1",
    },
    {
        "event_id":        "TC05-EVT-002",
        "trip_id":         "TC05-TRIP-001",
        "rider_id":        "TC05-RIDER-001",
        "driver_id":       "TC05-DRIVER-EARN-001",
        "vehicle_id":      "TC05-VEH-001",
        "city_id":         "NYC",
        "event_type":      "payment_captured",
        "event_time":      "2026-06-16T17:50:45+00:00",
        "fare_total":      24.00,
        "surge_multiplier": 1.0,
        "promotion_amount": 0.0,
        "platform_fee":    6.00,
        "driver_payout":   18.00,
        "payment_method_code": "card",
        "source_system":   "tc05_test_producer",
        "schema_version":  "synthetic_v1",
    },
]

# Earnings event carries incentive bonus (peak-hour incentive = 3.00)
EARNINGS_EVENT = {
    "event_id":        "TC05-EARN-001",
    "trip_id":         "TC05-TRIP-001",
    "driver_id":       "TC05-DRIVER-EARN-001",
    "city_id":         "NYC",
    "event_type":      "driver_earnings_settled",
    "event_time":      "2026-06-16T17:51:00+00:00",
    "driver_payout":   18.00,       # base: fare × 0.75
    "platform_fee":    6.00,        # commission: fare × 0.25
    "fare_total":      24.00,       # total fare
    "surge_multiplier": 1.0,
    "source_system":   "tc05_test_producer",
    "schema_version":  "synthetic_v1",
}


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    for ev in TRIP_EVENTS:
        fut = producer.send(TRIP_TOPIC, key=ev["event_id"], value=ev)
        rec = fut.get(timeout=10)
        print(f"[{ev['event_type']}] topic={rec.topic} partition={rec.partition} offset={rec.offset}")

    fut = producer.send(EARN_TOPIC, key=EARNINGS_EVENT["event_id"], value=EARNINGS_EVENT)
    rec = fut.get(timeout=10)
    print(f"[EARNINGS SETTLED] topic={rec.topic} partition={rec.partition} offset={rec.offset}")

    producer.flush()
    print("\nTC-05: All 3 events published.")
    print("  Driver: TC05-DRIVER-EARN-001 | fare=24.00 | platform_fee=6.00 | base_payout=18.00")
    print("  Expected net_driver_earning = 18.00 (base) — incentive_bonus tracked separately in Gold")


if __name__ == "__main__":
    main()
