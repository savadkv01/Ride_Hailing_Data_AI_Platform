"""
sync_events_to_mongodb.py
Reads operational events from staging.silver_canonical_events (PostgreSQL)
and syncs them into the three MongoDB collections:
  - fraud_cases       ← event_type = 'fraud_signal'
  - support_tickets   ← event_type = 'support_ticket_created'
  - rider_app_sessions← rider sessions grouped from trip events
Architecture: Silver → MongoDB (operational document store) → FastAPI /api/v1/ops/*
"""
import os
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.env_loader import auto_load_env

auto_load_env(project_root=PROJECT_ROOT)

try:
    from pymongo import MongoClient, UpdateOne
except ImportError:
    print("ERROR: pymongo not installed. Run: pip install pymongo")
    sys.exit(1)


# ── connections ───────────────────────────────────────────────────────────────

def pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "ride_warehouse"),
        user=os.getenv("POSTGRES_USER", "ride_admin"),
        password=os.getenv("POSTGRES_PASSWORD", "ride_password"),
    )


def mongo_db():
    uri = os.getenv(
        "MONGO_URI",
        f"mongodb://{os.getenv('MONGO_ROOT_USERNAME','ride_mongo_admin')}:{os.getenv('MONGO_ROOT_PASSWORD','ride_mongo_password')}@localhost:27017",
    )
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client["ride_hailing_ops"]


# ── sync fraud cases ──────────────────────────────────────────────────────────

def sync_fraud_cases(pg, db):
    sql = """
        SELECT event_id, trip_id, driver_id, rider_id, city_id,
               event_type, event_time, fraud_score, fare_total,
               surge_multiplier, source_system
        FROM staging.silver_canonical_events
        WHERE event_type IN ('fraud_signal', 'ghost_trip_detected', 'fraud_detected')
        ORDER BY event_time DESC
    """
    with pg.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    if not rows:
        print("  fraud_cases: 0 events found in Silver")
        return 0

    ops = []
    for r in rows:
        doc = {
            "fraud_case_id": r["event_id"],
            "trip_id": r["trip_id"],
            "driver_id": r["driver_id"],
            "rider_id": r["rider_id"],
            "city_id": r["city_id"],
            "event_type": r["event_type"],
            "event_time": str(r["event_time"]),
            "fraud_score": float(r["fraud_score"]) if r["fraud_score"] else None,
            "final_fare": float(r["fare_total"]) if r["fare_total"] else None,
            "surge_multiplier": float(r["surge_multiplier"]) if r["surge_multiplier"] else 1.0,
            "source_system": r["source_system"],
            "risk_band": _risk_band(r["fraud_score"]),
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ops.append(UpdateOne({"fraud_case_id": doc["fraud_case_id"]}, {"$set": doc}, upsert=True))

    result = db["fraud_cases"].bulk_write(ops)
    print(f"  fraud_cases: upserted={result.upserted_count} modified={result.modified_count} total={len(rows)}")
    return len(rows)


def _risk_band(score):
    if score is None:
        return "unknown"
    s = float(score)
    if s >= 0.8:
        return "high"
    if s >= 0.5:
        return "medium"
    return "low"


# ── sync support tickets ──────────────────────────────────────────────────────

def sync_support_tickets(pg, db):
    sql = """
        SELECT event_id, trip_id, driver_id, rider_id, city_id,
               event_type, event_time, source_system
        FROM staging.silver_canonical_events
        WHERE event_type IN ('support_ticket_created', 'complaint_raised', 'refund_requested')
        ORDER BY event_time DESC
    """
    with pg.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    if not rows:
        print("  support_tickets: 0 events found in Silver")
        return 0

    ops = []
    for r in rows:
        doc = {
            "support_ticket_id": r["event_id"],
            "trip_id": r["trip_id"],
            "rider_id": r["rider_id"],
            "driver_id": r["driver_id"],
            "city_id": r["city_id"],
            "issue_type": r["event_type"],
            "description": f"Auto-synced from Silver: {r['event_type']} for trip {r['trip_id']}",
            "status": "open",
            "event_time": str(r["event_time"]),
            "source_system": r["source_system"],
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ops.append(UpdateOne({"support_ticket_id": doc["support_ticket_id"]}, {"$set": doc}, upsert=True))

    result = db["support_tickets"].bulk_write(ops)
    print(f"  support_tickets: upserted={result.upserted_count} modified={result.modified_count} total={len(rows)}")
    return len(rows)


# ── sync rider app sessions ───────────────────────────────────────────────────

def sync_rider_app_sessions(pg, db):
    sql = """
        SELECT rider_id, city_id,
               COUNT(*) FILTER (WHERE event_type = 'ride_requested')   AS requests,
               COUNT(*) FILTER (WHERE event_type = 'trip_completed')   AS completions,
               COUNT(*) FILTER (WHERE event_type = 'trip_cancelled')   AS cancellations,
               MIN(event_time) AS first_seen,
               MAX(event_time) AS last_seen
        FROM staging.silver_canonical_events
        WHERE rider_id IS NOT NULL
          AND event_type IN ('ride_requested', 'trip_completed', 'trip_cancelled')
        GROUP BY rider_id, city_id
        ORDER BY last_seen DESC
    """
    with pg.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    if not rows:
        print("  rider_app_sessions: 0 riders found in Silver")
        return 0

    ops = []
    for r in rows:
        session_id = f"session_{r['rider_id']}_{r['city_id']}"
        doc = {
            "session_id": session_id,
            "rider_id": r["rider_id"],
            "city_id": r["city_id"],
            "total_requests": int(r["requests"]),
            "total_completions": int(r["completions"]),
            "total_cancellations": int(r["cancellations"]),
            "completion_rate": round(
                int(r["completions"]) / max(int(r["requests"]), 1), 3
            ),
            "first_seen": str(r["first_seen"]),
            "event_time": str(r["last_seen"]),
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ops.append(UpdateOne({"session_id": session_id}, {"$set": doc}, upsert=True))

    result = db["rider_app_sessions"].bulk_write(ops)
    print(f"  rider_app_sessions: upserted={result.upserted_count} modified={result.modified_count} total={len(rows)}")
    return len(rows)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== sync_events_to_mongodb ===")
    pg = pg_conn()
    db = mongo_db()

    # Verify MongoDB connection
    db.command("ping")
    print("MongoDB connected:", db.name)

    fraud_count = sync_fraud_cases(pg, db)
    ticket_count = sync_support_tickets(pg, db)
    session_count = sync_rider_app_sessions(pg, db)

    pg.close()
    total = fraud_count + ticket_count + session_count
    print(f"\nSync complete — {total} documents synced across 3 collections.")
    print(f"  fraud_cases:        {fraud_count}")
    print(f"  support_tickets:    {ticket_count}")
    print(f"  rider_app_sessions: {session_count}")


if __name__ == "__main__":
    main()
