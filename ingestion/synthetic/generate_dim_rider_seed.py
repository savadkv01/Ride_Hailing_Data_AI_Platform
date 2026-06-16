import json
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "rider_id": rid("rider"),
        "city_id": rand_city(),
        "signup_ts": now_iso(),
        "rider_segment": "standard",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
