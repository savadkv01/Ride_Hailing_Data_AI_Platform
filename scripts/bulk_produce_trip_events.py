"""
bulk_produce_trip_events.py
Publishes 220 trips × 5 events (1,100 total) to Kafka for bulk Gold population.

Event window: 2026-06-16T17:52:00Z → 2026-06-16T18:17:40Z  (~25 min, safely within the
30-min Silver watermark: current max event_time = 17:51, watermark threshold = 17:21)

Cities: NYC (80), CHI (70), DXB (40), MIA (30)
Topics:
  rh.trip.lifecycle.events.v1  — ride_requested, driver_assigned, trip_started,
                                  trip_completed, payment_captured
  rh.earnings.events.v1        — driver_earnings_settled (one per trip_completed)
"""
import json
import random
import sys
from datetime import datetime, timezone, timedelta

from kafka import KafkaProducer

BOOTSTRAP = "localhost:9094"
TRIP_TOPIC = "rh.trip.lifecycle.events.v1"
EARN_TOPIC = "rh.earnings.events.v1"

CITY_DIST = (
    [("NYC", 80, 15.0, 45.0, 1.0)] +
    [("CHI", 70, 10.0, 32.0, 1.0)] * 1 +    # some CHI trips get surge below
    [("DXB", 40, 20.0, 60.0, 1.0)] +
    [("MIA", 30, 12.0, 35.0, 1.0)]
)

PAYMENT_METHODS = ["card", "wallet", "cash", "card", "wallet"]  # card most common

BASE_TS = datetime(2026, 6, 16, 17, 52, 0, tzinfo=timezone.utc)
TRIP_GAP_S = 7       # seconds between trip starts
EVENT_GAP_S = 1      # seconds between events within a trip

random.seed(42)      # reproducible

TRIPS = []
city_pool = (
    ["NYC"] * 80 + ["CHI"] * 70 + ["DXB"] * 40 + ["MIA"] * 30
)
random.shuffle(city_pool)

for i, city_id in enumerate(city_pool):
    fare_lo = {"NYC": 15.0, "CHI": 10.0, "DXB": 20.0, "MIA": 12.0}[city_id]
    fare_hi = {"NYC": 45.0, "CHI": 32.0, "DXB": 60.0, "MIA": 35.0}[city_id]
    base_fare = round(random.uniform(fare_lo, fare_hi), 2)

    # surge: 30 % of CHI trips get 1.5×, 20 % of NYC get 1.3×
    surge = 1.0
    if city_id == "CHI" and random.random() < 0.30:
        surge = 1.5
    elif city_id == "NYC" and random.random() < 0.20:
        surge = 1.3
    elif city_id == "DXB" and random.random() < 0.15:
        surge = 1.2

    fare_total = round(base_fare * surge, 2)
    platform_fee = round(fare_total * 0.25, 2)
    driver_payout = round(fare_total * 0.75, 2)

    rider_id = f"BULK-RIDER-{i % 100:04d}"
    driver_id = f"BULK-DRIVER-{i % 80:04d}"
    vehicle_id = f"BULK-VEH-{i % 80:04d}"
    trip_id = f"BULK-{city_id}-{i:04d}"
    payment_method = random.choice(PAYMENT_METHODS)

    trip_start = BASE_TS + timedelta(seconds=i * TRIP_GAP_S)

    events = [
        {
            "event_id":        f"{trip_id}-E1",
            "trip_id":         trip_id,
            "rider_id":        rider_id,
            "driver_id":       None,
            "vehicle_id":      None,
            "city_id":         city_id,
            "event_type":      "ride_requested",
            "event_time":      (trip_start).isoformat(),
            "fare_total":      None,
            "surge_multiplier": surge,
            "promotion_amount": 0.0,
            "platform_fee":    None,
            "driver_payout":   None,
            "payment_method_code": payment_method,
            "source_system":   "bulk_producer",
            "schema_version":  "synthetic_v1",
        },
        {
            "event_id":        f"{trip_id}-E2",
            "trip_id":         trip_id,
            "rider_id":        rider_id,
            "driver_id":       driver_id,
            "vehicle_id":      vehicle_id,
            "city_id":         city_id,
            "event_type":      "driver_assigned",
            "event_time":      (trip_start + timedelta(seconds=1)).isoformat(),
            "fare_total":      None,
            "surge_multiplier": surge,
            "promotion_amount": 0.0,
            "platform_fee":    None,
            "driver_payout":   None,
            "payment_method_code": payment_method,
            "source_system":   "bulk_producer",
            "schema_version":  "synthetic_v1",
        },
        {
            "event_id":        f"{trip_id}-E3",
            "trip_id":         trip_id,
            "rider_id":        rider_id,
            "driver_id":       driver_id,
            "vehicle_id":      vehicle_id,
            "city_id":         city_id,
            "event_type":      "trip_started",
            "event_time":      (trip_start + timedelta(seconds=2)).isoformat(),
            "fare_total":      None,
            "surge_multiplier": surge,
            "promotion_amount": 0.0,
            "platform_fee":    None,
            "driver_payout":   None,
            "payment_method_code": payment_method,
            "source_system":   "bulk_producer",
            "schema_version":  "synthetic_v1",
        },
        {
            "event_id":        f"{trip_id}-E4",
            "trip_id":         trip_id,
            "rider_id":        rider_id,
            "driver_id":       driver_id,
            "vehicle_id":      vehicle_id,
            "city_id":         city_id,
            "event_type":      "trip_completed",
            "event_time":      (trip_start + timedelta(seconds=4)).isoformat(),
            "fare_total":      fare_total,
            "surge_multiplier": surge,
            "promotion_amount": 0.0,
            "platform_fee":    platform_fee,
            "driver_payout":   driver_payout,
            "payment_method_code": payment_method,
            "source_system":   "bulk_producer",
            "schema_version":  "synthetic_v1",
        },
        {
            "event_id":        f"{trip_id}-E5",
            "trip_id":         trip_id,
            "rider_id":        rider_id,
            "driver_id":       driver_id,
            "vehicle_id":      vehicle_id,
            "city_id":         city_id,
            "event_type":      "payment_captured",
            "event_time":      (trip_start + timedelta(seconds=5)).isoformat(),
            "fare_total":      fare_total,
            "surge_multiplier": surge,
            "promotion_amount": 0.0,
            "platform_fee":    platform_fee,
            "driver_payout":   driver_payout,
            "payment_method_code": payment_method,
            "source_system":   "bulk_producer",
            "schema_version":  "synthetic_v1",
        },
    ]
    TRIPS.append({
        "trip_id": trip_id,
        "driver_id": driver_id,
        "city_id": city_id,
        "fare_total": fare_total,
        "platform_fee": platform_fee,
        "driver_payout": driver_payout,
        "surge_multiplier": surge,
        "earn_time": (trip_start + timedelta(seconds=6)).isoformat(),
        "events": events,
    })


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    trip_count = len(TRIPS)
    event_count = sum(len(t["events"]) for t in TRIPS)
    print(f"Publishing {trip_count} trips × 5 events = {event_count} events")
    print(f"  Time window: {TRIPS[0]['events'][0]['event_time']}  →  {TRIPS[-1]['events'][-1]['event_time']}")

    for i, trip in enumerate(TRIPS):
        for ev in trip["events"]:
            fut = producer.send(TRIP_TOPIC, key=ev["event_id"], value=ev)
            fut.get(timeout=10)

        # Earnings settlement event
        earn_ev = {
            "event_id":        f"{trip['trip_id']}-EARN",
            "trip_id":         trip["trip_id"],
            "driver_id":       trip["driver_id"],
            "city_id":         trip["city_id"],
            "event_type":      "driver_earnings_settled",
            "event_time":      trip["earn_time"],
            "fare_total":      trip["fare_total"],
            "platform_fee":    trip["platform_fee"],
            "driver_payout":   trip["driver_payout"],
            "surge_multiplier": trip["surge_multiplier"],
            "source_system":   "bulk_producer",
            "schema_version":  "synthetic_v1",
        }
        fut = producer.send(EARN_TOPIC, key=earn_ev["event_id"], value=earn_ev)
        fut.get(timeout=10)

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{trip_count}] Published trip {trip['trip_id']} city={trip['city_id']}")

    producer.flush()
    total = event_count + trip_count  # 5 trip events + 1 earnings per trip
    print(f"\nDone. {total} total events published to Kafka.")
    print(f"  Trip lifecycle topic: {event_count} events")
    print(f"  Earnings topic:       {trip_count} events")
    city_counts = {}
    for t in TRIPS:
        city_counts[t["city_id"]] = city_counts.get(t["city_id"], 0) + 1
    for city, cnt in sorted(city_counts.items()):
        print(f"    {city}: {cnt} trips")


if __name__ == "__main__":
    main()
