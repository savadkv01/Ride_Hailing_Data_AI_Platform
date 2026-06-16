import json
from ingestion.synthetic.common import rid


def generate() -> dict:
    return {
        "vehicle_id": rid("veh"),
        "vehicle_type": "sedan",
        "capacity": 4,
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
