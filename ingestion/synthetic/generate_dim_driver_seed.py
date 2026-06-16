import json
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "driver_id": rid("driver"),
        "city_id": rand_city(),
        "onboarding_ts": now_iso(),
        "driver_tier": "gold",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
