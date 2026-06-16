import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid

EVENTS = ["app_open", "search_ride", "request_ride", "cancel_ride"]


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "session_id": rid("sess"),
        "rider_id": rid("rider"),
        "city_id": rand_city(),
        "event_name": random.choice(EVENTS),
        "screen_name": "home",
        "event_time": now_iso(),
        "app_version": "6.2.1",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
