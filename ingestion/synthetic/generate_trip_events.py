import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    trip_id = rid("trip")
    fare_total = round(random.uniform(6, 180), 2)
    surge_multiplier = round(random.uniform(1.0, 2.8), 2)
    promotion_amount = round(random.uniform(0, 12), 2)
    platform_fee = round(fare_total * random.uniform(0.12, 0.30), 2)
    driver_payout = round(fare_total - platform_fee - promotion_amount, 2)
    return {
        "event_id": rid("evt"),
        "trip_id": trip_id,
        "rider_id": rid("rider"),
        "driver_id": rid("driver"),
        "vehicle_id": rid("veh"),
        "city_id": rand_city(),
        "event_type": "trip_completed",
        "event_time": now_iso(),
        "ingestion_time": now_iso(),
        "fare_total": fare_total,
        "surge_multiplier": surge_multiplier,
        "promotion_amount": promotion_amount,
        "platform_fee": platform_fee,
        "driver_payout": driver_payout,
        "payment_method_code": random.choice(["card", "wallet", "cash"]),
        "source_system": "synthetic_generator",
        "source_record_id": rid("src"),
        "schema_version": "synthetic_v1",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
