import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "incentive_id": rid("inc"),
        "driver_id": rid("driver"),
        "trip_id": rid("trip"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "incentive_type": random.choice(["quest", "peak_bonus", "guarantee"]),
        "incentive_amount": round(random.uniform(2, 30), 2),
        "eligibility_status": "eligible",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
