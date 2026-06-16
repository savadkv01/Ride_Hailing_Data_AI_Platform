import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "support_ticket_id": rid("ticket"),
        "trip_id": rid("trip"),
        "rider_id": rid("rider"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "ticket_status": random.choice(["open", "in_progress", "resolved"]),
        "category": random.choice(["billing", "safety", "app_issue"]),
        "severity": random.choice(["low", "medium", "high"]),
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
