import json
from ingestion.synthetic.common import rand_city, rid


def generate() -> dict:
    return {
        "doc_id": rid("doc"),
        "source_type": "faq",
        "city_id": rand_city(),
        "text": "FAQ: How is surge pricing calculated? It depends on real-time demand and supply imbalance.",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
