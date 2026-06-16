import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    score = round(random.uniform(0, 1), 4)
    band = "high" if score > 0.8 else "medium" if score > 0.5 else "low"
    action = "block" if band == "high" else "review" if band == "medium" else "allow"
    return {
        "event_id": rid("evt"),
        "fraud_case_id": rid("fraud"),
        "trip_id": rid("trip"),
        "rider_id": rid("rider"),
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "fraud_score": score,
        "risk_band": band,
        "action_taken": action,
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
