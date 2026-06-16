import json
from ingestion.synthetic.common import rand_city, rid


def generate() -> dict:
    return {
        "doc_id": rid("doc"),
        "source_type": "review",
        "city_id": rand_city(),
        "text": "Driver was on time and vehicle was clean.",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
