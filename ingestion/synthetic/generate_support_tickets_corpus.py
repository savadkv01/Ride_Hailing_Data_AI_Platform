import json
from ingestion.synthetic.common import rand_city, rid


def generate() -> dict:
    return {
        "doc_id": rid("doc"),
        "source_type": "support_ticket",
        "city_id": rand_city(),
        "text": "Rider reported incorrect fare and requested adjustment.",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
