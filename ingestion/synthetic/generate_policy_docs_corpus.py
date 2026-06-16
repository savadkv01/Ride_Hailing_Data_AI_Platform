import json
from ingestion.synthetic.common import rand_city, rid


def generate() -> dict:
    return {
        "doc_id": rid("doc"),
        "source_type": "policy_doc",
        "city_id": rand_city(),
        "text": "Platform policy: refunds are approved for verified service disruption cases.",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
