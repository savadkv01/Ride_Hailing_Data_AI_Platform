import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    completed = random.randint(100, 10000)
    requested = completed + random.randint(0, 1500)
    return {
        "event_id": rid("evt"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "requested_trips": requested,
        "completed_trips": completed,
        "active_drivers": random.randint(50, 5000),
        "avg_eta_sec": round(random.uniform(120, 900), 2),
        "avg_surge_multiplier": round(random.uniform(1.0, 3.0), 2),
        "gross_revenue": round(random.uniform(1000, 500000), 2),
        "net_revenue": round(random.uniform(500, 250000), 2),
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
