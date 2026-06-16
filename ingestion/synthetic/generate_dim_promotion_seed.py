import json
from ingestion.synthetic.common import rid


def generate() -> dict:
    return {
        "promotion_id": rid("promo"),
        "campaign_type": "coupon",
        "discount_type": "percent",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
