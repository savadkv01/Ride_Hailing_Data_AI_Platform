"""
TC-07 — Contract Validation Gate Test

Demonstrates two things:
1. The contract validator REJECTS the malformed event (fare_amount as string,
   city_id=null) with a non-zero exit code — contract is enforced.
2. A Bronze parquet row for the same event is written, Silver is expected to
   route it to quarantine_events (city_id IS NULL → quarantine predicate).

Usage:
    python scripts/tc07_contract_validation.py
"""
import json
import sys
import os
import tempfile
from datetime import datetime, timezone

import pandas as pd

# ── Add scripts/ to path so contract_validator importable ──────────────────
sys.path.insert(0, os.path.dirname(__file__))
from contract_validator import load_contract, validate_dataframe

CONTRACT_PATH = "config/contracts/op_trip_events_contract_v1.json"

# ── Malformed event (from TC-07 test spec) ──────────────────────────────────
BAD_EVENT = {
    "trip_id":         "TC07-BAD-001",
    "event_id":        "TC07-BAD-001-E1",
    "event_type":      "trip_completed",
    "fare_amount":     "18.50",          # VIOLATION: string instead of float
    "fare_total":      "18.50",          # VIOLATION: string instead of float
    "city_id":         None,             # VIOLATION: required field is null
    "rider_id":        "RIDER-007",
    "driver_id":       "DRIVER-007",
    "event_time":      "2026-06-17T10:00:00Z",
    "source_system":   "tc07_test",
    "schema_version":  "bad_v0",
    # deliberately missing: pickup_ts, dropoff_ts, distance_km, duration_sec,
    #                       source_record_id
}


def run_contract_validation():
    print("=" * 60)
    print("TC-07 Step 1 — Contract Validator (enforce mode)")
    print("=" * 60)

    df = pd.DataFrame([BAD_EVENT])
    contract = load_contract(CONTRACT_PATH)

    result = validate_dataframe(df, contract)
    errors = result.get("errors", [])

    print(f"\n  contract : {result['contract_name']} v{result['contract_version']}")
    print(f"  valid    : {result['valid']}")
    print(f"  rows     : {result['row_count']}")
    print(f"  errors   : {result['error_count']}")

    if errors:
        print(f"\nContract REJECTED — {len(errors)} violation(s):\n")
        for i, err in enumerate(errors, 1):
            print(f"  [{i}] {err}")
        print("\nResult: ENFORCE gate BLOCKS this event ✓")
    else:
        print("\nNo violations found — contract validator passed (unexpected)")

    return result


def write_bad_bronze_parquet():
    """
    Simulates what would land in Bronze if the event bypassed Kafka validation
    (warn mode or no gate). Writes a parquet to the Bronze op_trip_events
    partition for 2026-06-17 so Silver can process it.
    """
    print("\n" + "=" * 60)
    print("TC-07 Step 2 — Write malformed event to Bronze")
    print("=" * 60)

    row = {
        "event_id":       "TC07-BAD-001-E1",
        "trip_id":        "TC07-BAD-001",
        "rider_id":       "RIDER-007",
        "driver_id":      "DRIVER-007",
        "vehicle_id":     None,
        "city_id":        None,          # null — triggers Silver quarantine
        "event_type":     "trip_completed",
        "event_time":     "2026-06-17T10:00:00+00:00",
        "fare_total":     "18.50",        # wrong type — string
        "surge_multiplier": None,
        "promotion_amount": None,
        "platform_fee":   None,
        "driver_payout":  None,
        "payment_method_code": None,
        "source_system":  "tc07_bad_producer",
        "schema_version": "bad_v0",
        "ingest_date":    "2026-06-17",
    }

    # Write into Bronze partition where Silver will pick it up
    out_dir = "lakehouse/bronze/streaming/op_trip_events/ingest_date=2026-06-17"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "tc07-bad-event.parquet")

    df = pd.DataFrame([row])
    df.to_parquet(out_path, index=False)
    print(f"Written: {out_path}")
    print(f"  city_id = {row['city_id']}  (null → Silver will quarantine)")
    print(f"  fare_total = {repr(row['fare_total'])}  (string type)")
    return out_path


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))

    errors = run_contract_validation()
    write_bad_bronze_parquet()

    print("\n" + "=" * 60)
    print("Next: run Silver (trigger-once) then verify:")
    print("  - TC07-BAD-001-E1 NOT in staging.silver_canonical_events")
    print("  - TC07-BAD-001-E1     IN lakehouse/silver/quarantine_events/")
    print("=" * 60)

    # Non-zero exit if contract found violations (enforce mode)
    if not errors.get("valid", True):
        sys.exit(1)
