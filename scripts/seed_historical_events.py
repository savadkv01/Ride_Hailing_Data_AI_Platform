"""
seed_historical_events.py

Directly inserts trip_completed + payment_captured events into
staging.silver_canonical_events for June 10-15 (6 historical days).

This represents the backfill/historical-load operational pattern — used when
the Spark Silver streaming watermark prevents late-arriving historical data
from flowing through the standard streaming path.

After running, execute dbt to materialize the Gold tables:
  cd warehouse/dbt && dbt run
"""
import random
import uuid
from datetime import datetime, timezone, timedelta

import psycopg2

DB = dict(host="localhost", port=5432, dbname="ride_warehouse",
          user="ride_admin", password="ride_password")

# June 10 – June 15 (6 days), ~50 trips per day
# Timestamps per day: 09:00 – 09:28 UTC (within 30-min window per day)
DAYS = [
    (datetime(2026, 6, 10, 9, 0, 0, tzinfo=timezone.utc), 50),
    (datetime(2026, 6, 11, 9, 0, 0, tzinfo=timezone.utc), 55),
    (datetime(2026, 6, 12, 9, 0, 0, tzinfo=timezone.utc), 48),
    (datetime(2026, 6, 13, 9, 0, 0, tzinfo=timezone.utc), 62),   # Friday — higher
    (datetime(2026, 6, 14, 9, 0, 0, tzinfo=timezone.utc), 70),   # Saturday — peak
    (datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc), 58),   # Sunday
]

CITIES = ["NYC", "NYC", "NYC", "CHI", "CHI", "DXB", "MIA"]  # weighted pool
FARE_RANGE = {"NYC": (15, 45), "CHI": (10, 32), "DXB": (20, 60), "MIA": (12, 35)}

random.seed(99)

INSERT_SQL = """
INSERT INTO staging.silver_canonical_events (
    event_id, trip_id, rider_id, driver_id, vehicle_id, city_id,
    event_type, event_time, fare_total, surge_multiplier,
    promotion_amount, platform_fee, driver_payout,
    source_system, schema_version
) VALUES (
    %(event_id)s, %(trip_id)s, %(rider_id)s, %(driver_id)s, %(vehicle_id)s,
    %(city_id)s, %(event_type)s, %(event_time)s,
    %(fare_total)s, %(surge_multiplier)s, %(promotion_amount)s,
    %(platform_fee)s, %(driver_payout)s,
    %(source_system)s, %(schema_version)s
)
"""

def make_rows():
    rows = []
    for base_ts, n_trips in DAYS:
        for i in range(n_trips):
            city = random.choice(CITIES)
            lo, hi = FARE_RANGE[city]
            fare = round(random.uniform(lo, hi), 2)
            surge = 1.0
            if city == "CHI" and random.random() < 0.25:
                surge = 1.5
            elif city == "NYC" and random.random() < 0.20:
                surge = 1.3
            fare_total = round(fare * surge, 2)
            platform_fee = round(fare_total * 0.25, 2)
            driver_payout = round(fare_total * 0.75, 2)

            trip_id = f"HIST-{base_ts.strftime('%m%d')}-{city}-{i:04d}"
            rider_id = f"HIST-RIDER-{i % 100:04d}"
            driver_id = f"HIST-DRIVER-{i % 60:04d}"
            vehicle_id = f"HIST-VEH-{i % 60:04d}"
            t_completed = base_ts + timedelta(seconds=i * 10 + 4)
            t_payment   = base_ts + timedelta(seconds=i * 10 + 5)
            pay_method  = random.choice(["card", "wallet", "cash", "card"])

            # trip_completed
            rows.append({
                "event_id":          f"{trip_id}-TC",
                "trip_id":           trip_id,
                "rider_id":          rider_id,
                "driver_id":         driver_id,
                "vehicle_id":        vehicle_id,
                "city_id":           city,
                "event_type":        "trip_completed",
                "event_time":        t_completed,
                "fare_total":        fare_total,
                "surge_multiplier":  surge,
                "promotion_amount":  0.0,
                "platform_fee":      platform_fee,
                "driver_payout":     driver_payout,
                "source_system":     "historical_seed",
                "schema_version":    "synthetic_v1",
            })
            # payment_captured
            rows.append({
                "event_id":          f"{trip_id}-PC",
                "trip_id":           trip_id,
                "rider_id":          rider_id,
                "driver_id":         driver_id,
                "vehicle_id":        vehicle_id,
                "city_id":           city,
                "event_type":        "payment_captured",
                "event_time":        t_payment,
                "fare_total":        fare_total,
                "surge_multiplier":  surge,
                "promotion_amount":  0.0,
                "platform_fee":      platform_fee,
                "driver_payout":     driver_payout,
                "source_system":     "historical_seed",
                "schema_version":    "synthetic_v1",
            })
    return rows


def main():
    rows = make_rows()
    print(f"Inserting {len(rows)} historical rows into staging.silver_canonical_events ...")

    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor()
    count = 0
    for row in rows:
        cur.execute(INSERT_SQL, row)
        count += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    day_counts = {}
    for row in rows[::2]:  # every other row (trip_completed)
        d = str(row["event_time"].date())
        day_counts[d] = day_counts.get(d, 0) + 1
    print(f"  Inserted {count} rows ({len(rows)//2} trips across {len(DAYS)} days):")
    for day, cnt in sorted(day_counts.items()):
        print(f"    {day}: {cnt} trips")
    print("Done. Run dbt to materialize Gold.")


if __name__ == "__main__":
    main()
