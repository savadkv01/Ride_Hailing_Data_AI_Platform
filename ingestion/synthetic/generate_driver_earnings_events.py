import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    base = round(random.uniform(5, 70), 2)
    incentive = round(random.uniform(0, 20), 2)
    tip = round(random.uniform(0, 15), 2)
    return {
        "event_id": rid("evt"),
        "earning_id": rid("earn"),
        "trip_id": rid("trip"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "base_earning": base,
        "surge_bonus": round(random.uniform(0, 25), 2),
        "incentive_bonus": incentive,
        "tip_amount": tip,
        "adjustment_amount": 0.0,
        "net_driver_earning": round(base + incentive + tip, 2),
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
