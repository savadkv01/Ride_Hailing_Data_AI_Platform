import json
from ingestion.synthetic.common import CITIES


def generate() -> dict:
    return {
        "city_id": CITIES[0],
        "country_code": "US",
        "timezone": "UTC",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
