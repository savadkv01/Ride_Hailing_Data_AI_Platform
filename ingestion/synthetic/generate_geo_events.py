import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "trip_id": rid("trip"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "latitude": round(random.uniform(-90, 90), 6),
        "longitude": round(random.uniform(-180, 180), 6),
        "geohash": "dr5ru",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
