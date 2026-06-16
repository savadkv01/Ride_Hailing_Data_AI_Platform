import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    amount = round(random.uniform(5, 120), 2)
    return {
        "event_id": rid("evt"),
        "payment_id": rid("pay"),
        "trip_id": rid("trip"),
        "rider_id": rid("rider"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "amount": amount,
        "payment_status": "captured",
        "gateway_ref": rid("gw"),
        "method_code": random.choice(["card", "wallet", "cash"]),
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
