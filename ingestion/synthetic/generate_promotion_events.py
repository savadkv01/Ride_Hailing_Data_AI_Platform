import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "promotion_id": rid("promo"),
        "trip_id": rid("trip"),
        "rider_id": rid("rider"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "event_type": "promotion_redeemed",
        "promotion_amount": round(random.uniform(1, 15), 2),
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
