import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    surge = round(random.uniform(1.0, 3.5), 2)
    return {
        "event_id": rid("evt"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "avg_surge_multiplier": surge,
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
