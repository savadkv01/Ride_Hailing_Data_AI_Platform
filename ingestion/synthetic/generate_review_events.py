import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "review_id": rid("review"),
        "trip_id": rid("trip"),
        "rider_id": rid("rider"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "rating_value": random.randint(1, 5),
        "review_text": "Driver was professional and route was efficient.",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
