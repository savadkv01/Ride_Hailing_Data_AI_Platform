"""
TC-04 data seeder: inject multiple churn-pattern riders into gold.fact_trip
Creates 20 riders who had trips in April-May then returned in June (churned_7d=1 historical rows)
and 20 consistently active riders (churned_7d=0) for class diversity.
"""
import psycopg2
import hashlib

HOST = "localhost"
PORT = 5432
DB   = "ride_warehouse"
USER = "ride_admin"
PASS = "ride_password"

def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

rows = []

# 20 CHURN-PATTERN riders: old trips in April/May, returned Jun 16
for i in range(1, 21):
    rid = f"TC04-CHURN-{i:03d}"
    for day_offset, date_str, time_key in [
        (0, "2026-04-10", 2026041009),
        (5, "2026-04-15", 2026041509),
        (10,"2026-04-20", 2026042009),
    ]:
        rows.append((
            f"tc04c{i:03d}d{day_offset}", f"TC04-CTRIP-{i}-{day_offset}",
            md5(rid), md5("DRV-X"), md5("VEH-X"), md5("NYC"),
            time_key, md5("0"), md5("tc04"),
            14.00, 1.0, 0, 3.50, 10.50, 1, 0,
            f"2026-04-{10+day_offset:02d} 09:00:00"
        ))
    # Return trip in June
    rows.append((
        f"tc04c{i:03d}ret", f"TC04-CTRIP-{i}-RET",
        md5(rid), md5("DRV-X"), md5("VEH-X"), md5("NYC"),
        2026061618, md5("0"), md5("tc04"),
        18.00, 1.0, 0, 4.50, 13.50, 1, 0,
        "2026-06-16 18:00:00"
    ))

# 20 ACTIVE riders: trips every 2 days in June
for i in range(1, 21):
    rid = f"TC04-ACTIVE-{i:03d}"
    for day in [1, 3, 5, 8, 10, 12, 14, 16]:
        rows.append((
            f"tc04a{i:03d}d{day}", f"TC04-ATRIP-{i}-{day}",
            md5(rid), md5("DRV-Y"), md5("VEH-Y"), md5("CHI"),
            int(f"2026060{day:d}08") if day < 10 else int(f"20260{6}{day}08"),
            md5("0"), md5("tc04"),
            16.00, 1.0, 0, 4.00, 12.00, 1, 0,
            f"2026-06-{day:02d} 08:00:00"
        ))

conn = psycopg2.connect(host=HOST, port=PORT, dbname=DB, user=USER, password=PASS)
with conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gold.fact_trip WHERE trip_id LIKE 'TC04-%'")
        cur.executemany(
            """INSERT INTO gold.fact_trip (
                trip_fact_key, trip_id, rider_key, driver_key, vehicle_key, city_key,
                time_key, promotion_key, payment_method_key,
                final_fare, surge_multiplier, promotion_amount, platform_fee, driver_payout,
                completed_flag, cancelled_flag, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            rows
        )
        cur.execute("SELECT COUNT(*) FROM gold.fact_trip WHERE trip_id LIKE 'TC04-%'")
        n = cur.fetchone()[0]
        print(f"TC-04 Gold rows inserted: {n}")
conn.close()
