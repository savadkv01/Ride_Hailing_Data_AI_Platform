import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    return {
        "event_id": rid("evt"),
        "refund_id": rid("refund"),
        "payment_id": rid("pay"),
        "trip_id": rid("trip"),
        "rider_id": rid("rider"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "refund_amount": round(random.uniform(1, 50), 2),
        "refund_reason": "service_issue",
        "refund_status": "approved",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
