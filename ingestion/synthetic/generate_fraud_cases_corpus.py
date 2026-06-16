import json
from ingestion.synthetic.common import rand_city, rid


def generate() -> dict:
    return {
        "doc_id": rid("doc"),
        "source_type": "fraud_case",
        "city_id": rand_city(),
        "text": "Fraud investigation: repeated rider-driver pair trips within implausibly short intervals.",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
