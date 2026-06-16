import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "latitude": round(random.uniform(-90, 90), 6),
        "longitude": round(random.uniform(-180, 180), 6),
        "speed_kph": round(random.uniform(0, 95), 2),
        "bearing": round(random.uniform(0, 360), 2),
        "online_status": random.choice(["online", "busy", "offline"]),
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
