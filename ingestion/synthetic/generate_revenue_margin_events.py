import json
import random
from ingestion.synthetic.common import now_iso, rand_city, rid


def generate() -> dict:
    gross = round(random.uniform(10, 200), 2)
    platform_fee = round(gross * random.uniform(0.12, 0.30), 2)
    incentive = round(random.uniform(0, 15), 2)
    refund = round(random.uniform(0, 10), 2)
    net = round(gross - incentive - refund, 2)
    margin = round(net - random.uniform(1, 20), 2)
    return {
        "event_id": rid("evt"),
        "trip_id": rid("trip"),
        "city_id": rand_city(),
        "event_time": now_iso(),
        "gross_booking_amount": gross,
        "platform_fee_amount": platform_fee,
        "incentive_cost_amount": incentive,
        "refund_amount": refund,
        "net_revenue_amount": net,
        "contribution_margin_amount": margin,
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
