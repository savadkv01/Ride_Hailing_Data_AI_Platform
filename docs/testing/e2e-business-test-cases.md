# End-to-End Business Test Cases

These test cases validate the platform from the perspective of real business outcomes,  
tracing data through every layer: event source → Bronze → Silver → Gold → Warehouse → ML / RAG → API → Observability.

Each test case is written for a human reviewer to walk through — not a syntax check.  
Pass/fail decisions are based on whether the **business outcome** is correct, not just whether code ran.

---

## Test Case Index

| ID | Business Scenario | Layers Touched |
|----|-------------------|---------------|
| TC-01 | Rider completes a trip — happy path end-to-end | Kafka → Bronze → Silver → Gold → Warehouse → API |
| TC-02 | Surge pricing activates during peak demand | Kafka → Bronze → Silver → Gold → ML inference → API |
| TC-03 | Fraudulent trip payment is detected and flagged | Kafka → Bronze → Silver → Gold → ML inference → Audit |
| TC-04 | At-risk rider is identified for churn prevention | Gold → ML feature pipeline → ML model → API |
| TC-05 | Driver earnings are settled correctly after a trip | Kafka → Bronze → Silver → Gold → Warehouse |
| TC-06 | City operations team reviews daily KPI dashboard | Gold → mart_city_daily_kpis → Grafana / API |
| TC-07 | Producer sends an event that violates the data contract | Kafka → Contract validator → Quarantine / Block |
| TC-08 | Support agent asks the RAG assistant a refund policy question | Weaviate → RAG assistant → API → grounded answer |
| TC-09 | Demand forecast informs city driver supply planning | Gold → ML feature pipeline → demand model → forecast output |
| TC-10 | Pipeline failure is detected and surfaced in observability | ML/Airflow → pipeline_run_audit → Prometheus alert |
| TC-11 | Operational events are stored and queryable in MongoDB | Silver → MongoDB sync → FastAPI /api/v1/ops/* |
| TC-12 | Grafana dashboard shows live KPIs from the warehouse | Gold → PostgreSQL → Grafana provisioned dashboard |

---

## TC-01 — Rider Completes a Trip (Happy Path End-to-End)

**Business context:**  
A rider in New York City requests a standard ride, a driver accepts and completes the trip, payment is captured, and both parties leave a 5-star review. This is the core revenue-generating event the entire platform is built around.

**Pre-conditions**
- Synthetic trip event producer is running (`generate_trip_events.py`).
- Kafka topic `op.trip_events` exists and is healthy.
- Spark streaming jobs (Bronze, Silver, Gold) are running.
- dbt has been run at least once against the Silver output.
- PostgreSQL warehouse is reachable.
- FastAPI service is up on `localhost:8000`.

**Test data (injected via synthetic producer)**

| Field | Value |
|-------|-------|
| `trip_id` | `TC01-TRIP-001` |
| `event_type` | sequence: `ride_requested` → `driver_assigned` → `trip_started` → `trip_completed` → `payment_captured` → `review_submitted` |
| `city_id` | `NYC` |
| `rider_id` | `RIDER-001` |
| `driver_id` | `DRIVER-001` |
| `base_fare` | 18.50 |
| `total_fare` | 21.00 (includes platform fee) |
| `rating` | 5 |
| `event_time` | 2026-06-16T09:00:00Z |

**Steps and expected outcomes per layer**

**Step 1 — Bronze layer (raw durability)**
- Expected: All 6 events for `TC01-TRIP-001` appear in `lakehouse/bronze/` as Parquet partitions under `city_id=NYC/date=2026-06-16/`.
- Check: `event_id` values are globally unique and non-null. `ingestion_time` is populated. No events are missing.
- Fail condition: Any event is absent, duplicated, or has a null `event_id`.

**Step 2 — Silver layer (canonical form)**
- Expected: Events are normalized to the canonical schema (`op_trip_events_contract_v1`). `rider_id` and `driver_id` are pseudonymous keys. `event_type` maps correctly to the canonical lifecycle enum.
- Check: Query `staging.silver_canonical_events` — all 6 rows for `TC01-TRIP-001` are present with correct `event_type` values and no null `fare_amount` on `trip_completed`.
- Fail condition: Any missing lifecycle step, or a `trip_completed` row with null fare.

**Step 3 — Gold / Warehouse (facts and dimensions)**
- Expected: `fact_trip` has one row for `TC01-TRIP-001` with `trip_status = completed`. `fact_payment` has one row with `payment_status = captured` and `total_amount = 21.00`. `fact_review` has one row with `rating = 5`. `dim_rider` has a current row for `RIDER-001`. `dim_driver` has a current row for `DRIVER-001`.
- Check: Run dbt, then query each table.
- Fail condition: Trip row missing, wrong status, payment amount mismatch, or review not recorded.

**Step 4 — KPI mart**
- Expected: `mart_city_daily_kpis` for `city_id = NYC`, `event_date = 2026-06-16` shows `completed_trips` incremented by 1, `gross_fare_total` increased by 21.00, and `avg_rider_rating` reflects the 5-star review.
- Fail condition: KPI row absent or counters unchanged.

**Step 5 — API**
- Expected: `GET /api/v1/analytics/city-kpis?city=NYC&date=2026-06-16` returns a payload with `completed_trips ≥ 1` and `gross_fare_total > 0`.
- Fail condition: 404, empty result, or wrong city/date.

**Pass criteria:**  
All 5 steps pass → the core revenue event flows correctly from source to every downstream layer.

---

## TC-02 — Surge Pricing Activates During Peak Demand

**Business context:**  
It is Friday evening rush hour in Chicago. Ride requests spike above the baseline threshold. The platform must detect elevated demand, apply a surge multiplier, record surge-priced trips in the lakehouse, and make the surge signal available to the ML surge model and the API.

**Pre-conditions**
- `generate_surge_pricing_events.py` and `generate_trip_events.py` running at elevated rate.
- Spark Silver and Gold jobs running.
- Surge model artifact (`ml/artifacts/surge_model.joblib`) exists.
- FastAPI `/api/v1/model/surge` endpoint is reachable.

**Test data**

| Field | Value |
|-------|-------|
| `city_id` | `CHI` |
| `hour_of_day` | 17–19 (peak window) |
| `event_type` | `surge_activated` + corresponding `trip_completed` events |
| `surge_multiplier` | 1.8 |
| `trip_count_in_window` | 120 (exceeds baseline of 60) |
| `base_fare` | 14.00 |
| `surged_fare` | 25.20 (14.00 × 1.8) |

**Steps and expected outcomes per layer**

**Step 1 — Bronze**
- Expected: `surge_activated` events present in bronze for `CHI` with `surge_multiplier = 1.8`. `trip_completed` events in the same window carry non-null `surge_multiplier`.

**Step 2 — Silver**
- Expected: Canonical events include `surge_multiplier` field populated. `fare_amount` on surge trips reflects the multiplied value.
- Fail condition: `surge_multiplier` null or zero on affected trips.

**Step 3 — Gold**
- Expected: `fact_trip` rows for the peak window have `surge_multiplier = 1.8`. `mart_city_daily_kpis` for `CHI` shows `avg_surge_multiplier > 1.0` for the 2026-06-16 peak window.

**Step 4 — ML surge inference**
- Expected: Calling `POST /api/v1/model/surge` with `{"city_id": "CHI", "hour_of_day": 18, "ride_requests": 120}` returns `{"predicted_surge": ...}` with a value noticeably above 1.0.
- Fail condition: Model returns 1.0 (no surge detected) or 500 error.

**Pass criteria:**  
Surge signal propagates correctly through all layers and the ML endpoint reflects elevated pricing.

---

## TC-03 — Fraudulent Trip Payment is Detected and Flagged

**Business context:**  
A driver completes a ghost trip — the trip was never physically taken but payment was submitted. The fraud signal should appear in the event stream, pass through the lakehouse, be scored by the fraud ML model, and result in a record in `fact_fraud` for the Trust & Safety team to act on.

**Pre-conditions**
- `generate_fraud_signal_events.py` running.
- Fraud model artifact (`ml/artifacts/fraud_model.joblib`) exists.
- `fact_fraud` model in dbt is deployed.
- FastAPI `/api/v1/model/fraud` is reachable.

**Test data**

| Field | Value |
|-------|-------|
| `trip_id` | `TC03-TRIP-FRAUD-001` |
| `fraud_type` | `ghost_trip` |
| `city_id` | `NYC` |
| `driver_id` | `DRIVER-FRAUD-001` |
| `fare_amount` | 95.00 (abnormally high for distance) |
| `trip_distance_km` | 0.3 (abnormally short) |
| `payment_method` | `new_card` (first-time card) |
| `event_time` | 2026-06-16T02:15:00Z (off-peak) |

**Steps and expected outcomes per layer**

**Step 1 — Bronze**
- Expected: `fraud_signal` event with `TC03-TRIP-FRAUD-001` appears in bronze. No data dropped or modified.

**Step 2 — Silver**
- Expected: Canonical fraud event row present. `fraud_type` = `ghost_trip`. Fare-to-distance ratio signals an anomaly (fare >> expected for distance).

**Step 3 — Gold**
- Expected: `fact_fraud` has one row for `TC03-TRIP-FRAUD-001` with `fraud_type = ghost_trip` and status `flagged` or `under_review`. The linked `fact_trip` row exists.

**Step 4 — ML fraud scoring**
- Expected: `POST /api/v1/model/fraud` with the trip features returns `{"fraud_probability": ...}` with a value > 0.5 (classified as fraud-likely).
- Fail condition: Score < 0.5 or the endpoint errors.

**Step 5 — Audit trail**
- Expected: `metadata.pipeline_run_audit` records the ML scoring run with `status = success`.
- Fail condition: No audit row, or `status = failed`.

**Pass criteria:**  
Fraud signal is present from bronze through the warehouse, the model scores it as high-risk, and the audit trail confirms the run.

---

## TC-04 — At-Risk Rider Identified for Churn Prevention

**Business context:**  
A rider who was highly active 60 days ago has not taken a trip in 30 days. The churn model should identify this rider as at-risk so the promotions team can trigger a re-engagement incentive.

**Pre-conditions**
- Historical trip data exists for `RIDER-CHURN-001` with at least 5 completed trips before a 30-day gap.
- ML feature table `ml.feature_rider_churn_daily` has been built from gold.
- Churn model artifact (`ml/artifacts/churn_model.joblib`) exists.
- FastAPI `/api/v1/model/churn` is reachable.

**Test data (seeded in gold via dbt or fixture)**

| Field | Value |
|-------|-------|
| `rider_id` | `RIDER-CHURN-001` |
| `trips_last_30d` | 0 |
| `trips_prev_30d` | 7 |
| `days_since_last_trip` | 32 |
| `avg_rating_given` | 4.8 |
| `lifetime_trips` | 38 |
| `city_id` | `NYC` |

**Steps and expected outcomes**

**Step 1 — Feature table**
- Expected: `ml.feature_rider_churn_daily` has a row for `RIDER-CHURN-001` with `trips_last_30d = 0`, `days_since_last_trip = 32`. The activity drop-off is captured correctly.
- Fail condition: Row missing or activity counts wrong.

**Step 2 — Churn model inference**
- Expected: `POST /api/v1/model/churn` returns `{"churn_probability": ...}` > 0.6 for this rider's feature vector.
- Fail condition: Low probability (< 0.4) or error — the model has missed an obvious churn signal.

**Step 3 — Business action traceability**
- Expected: The rider appears in any at-risk segment query (e.g., filtered view on `ml.feature_rider_churn_daily` where `churn_probability > 0.5`). This list could be handed directly to the promotions team.
- Fail condition: Rider absent from at-risk output.

**Pass criteria:**  
The rider's activity gap is faithfully captured in the feature table and the churn model correctly identifies them as at-risk.

---

## TC-05 — Driver Earnings Settled Correctly After a Trip

**Business context:**  
After a trip completes, a driver's payout must be calculated accurately: base fare minus platform commission plus any active incentive. The driver and finance teams must be able to reconcile earnings from the warehouse.

**Pre-conditions**
- `generate_driver_earnings_events.py` and `generate_incentive_events.py` running.
- `fact_driver_earnings` and linked dims are deployed in dbt.

**Test data**

| Field | Value |
|-------|-------|
| `trip_id` | `TC05-TRIP-001` |
| `driver_id` | `DRIVER-EARN-001` |
| `city_id` | `NYC` |
| `total_fare` | 24.00 |
| `platform_commission_rate` | 0.25 (25%) |
| `incentive_bonus` | 3.00 (peak-hour incentive) |
| `expected_driver_payout` | 24.00 × (1 − 0.25) + 3.00 = **21.00** |

**Steps and expected outcomes per layer**

**Step 1 — Bronze / Silver**
- Expected: `driver_earnings` event for `TC05-TRIP-001` in bronze and silver. `gross_earning`, `commission_amount`, and `incentive_bonus` fields are non-null and present.

**Step 2 — Gold**
- Expected: `fact_driver_earnings` has one row for `TC05-TRIP-001` with:
  - `gross_earning = 18.00` (24.00 × 0.75)
  - `incentive_amount = 3.00`
  - `net_payout = 21.00`
- Fail condition: Any of these values is wrong, zero, or null.

**Step 3 — Reconciliation check**
- Expected: Summing `net_payout` in `fact_driver_earnings` for `DRIVER-EARN-001` matches what the driver would expect on their earnings statement.
- Fail condition: Discrepancy between sum of trip-level payouts and driver-level total.

**Pass criteria:**  
The driver payout arithmetic is correct end-to-end from event to warehouse — finance can rely on these numbers.

---

## TC-06 — City Operations Team Reviews Daily KPI Dashboard

**Business context:**  
Every morning, a city operations manager opens the Grafana dashboard or calls the API to review the previous day's performance: trips completed, completion rate, gross bookings, and average wait time. These numbers must be fresh, accurate, and consistent.

**Pre-conditions**
- At least 24 hours of synthetic event data has flowed through the pipeline.
- dbt has run successfully. `mart_city_daily_kpis` is populated.
- FastAPI analytics endpoint is reachable.
- Grafana/Prometheus monitoring stack is running.

**Test data (derived from pipeline output)**

| Expected KPI | Business rule |
|-------------|---------------|
| `total_requests` | Count of `ride_requested` events per city/day |
| `completed_trips` | Count of `trip_completed` events per city/day |
| `completion_rate` | `completed_trips / total_requests` — must be between 0.70 and 1.0 for healthy operations |
| `gross_fare_total` | Sum of `total_fare` on `trip_completed` events |
| `avg_wait_time_minutes` | Avg time between `ride_requested` and `driver_arrived` |

**Steps and expected outcomes**

**Step 1 — KPI mart freshness**
- Expected: `max(event_date)` in `mart_city_daily_kpis` is no more than 24 hours behind the current timestamp.
- Fail condition: Data is stale (> 24 hours gap) — operations team sees yesterday's yesterday.

**Step 2 — KPI correctness**
- Expected: `completion_rate` for any active city is > 0.70. `gross_fare_total > 0`. No city row has negative fare.
- Fail condition: `completion_rate = 0` (likely a join gap) or negative fares (sign error in pipeline).

**Step 3 — API response**
- Expected: `GET /api/v1/analytics/city-kpis?city=NYC&date=2026-06-15` returns a JSON payload with all five KPI fields populated and matching warehouse values.
- Fail condition: Missing fields, nulls, or mismatch with direct DB query.

**Step 4 — Data quality audit**
- Expected: Running `python scripts/monitor_data_quality.py` produces a row in `metadata.data_quality_audit` for each of the three checks (`kpi_table_not_empty`, `kpi_table_freshness`, `kpi_negative_fares`) with `status = passed` and `violation_count = 0`.
- Verify:
  ```sql
  SELECT rule_id, status, violation_count, observed_at
  FROM metadata.data_quality_audit ORDER BY observed_at DESC LIMIT 3;
  ```
- Fail condition: DQ audit row shows `status = failed` for `kpi_table_freshness` — mart data is stale. Or table is empty — monitor has never been run.

**Pass criteria:**  
The operations team can open the dashboard and trust the numbers — they are fresh, non-negative, and match the API.

---

## TC-07 — Producer Sends an Event That Violates the Data Contract

**Business context:**  
A new engineering team onboards a new event producer but sends `fare_amount` as a string (`"18.50"`) instead of a float, and omits the required `city_id` field. The platform's governance layer must catch this before bad data reaches Silver and corrupts downstream models.

**Pre-conditions**
- Contract validator available: `scripts/contract_validator.py`.
- Active contract: `config/contracts/op_trip_events_contract_v1.json` (v1.0.0).
- Spark Silver job running (workers up: `rh-spark-worker-1`, `rh-spark-worker-2`).
- Bronze lakehouse mounted at `/opt/lakehouse/bronze/streaming` inside Spark master.

**Test data (malformed event)**

```json
{
  "trip_id":     "TC07-BAD-001",
  "event_id":    "TC07-BAD-001-E1",
  "event_type":  "trip_completed",
  "fare_amount": "18.50",
  "city_id":     null,
  "rider_id":    "RIDER-007",
  "driver_id":   "DRIVER-007",
  "event_time":  "2026-06-17T10:00:00Z"
}
```

Violations vs contract:
1. `fare_amount` is a string — contract requires `float`
2. `city_id` is `null` — listed in `quality_rules.not_null`
3. Missing required columns: `pickup_ts`, `dropoff_ts`, `distance_km`, `duration_sec`, `source_record_id`

**Execution**

Run the TC-07 script (Steps 1 + 2 combined):
```bash
python scripts/tc07_contract_validation.py
# Expected exit code: 1 (non-zero = enforce mode blocked)
```

Run Silver (Step 3):
```bash
docker exec rh-spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.driver.host=spark-master \
  --conf spark.driver.bindAddress=0.0.0.0 \
  /opt/spark/jobs/silver/silver_canonical_events.py \
  --bronze-root /opt/lakehouse/bronze/streaming \
  --silver-root /opt/lakehouse/silver \
  --checkpoint-root /opt/spark/checkpoints/silver \
  --trigger-once
```

**Steps and expected outcomes (validated 2026-06-17)**

**Step 1 — Contract validation gate (enforce mode) ✅**
- **Actual**: `contract_validator.py` returned exit code **1**. Detected **2 violations**:
  - `[1] Missing required columns: ['pickup_ts', 'dropoff_ts', 'distance_km', 'duration_sec', 'source_record_id']`
  - `[2] Column 'city_id' has 1 null values`
- `valid: False`, `error_count: 2`, contract `op_trip_events v1.0.0`
- The enforce gate blocks this event before it enters the pipeline.
- Fail condition: Event passes validation silently (`valid: True`) — contract not enforced.

**Step 2 — Bronze (simulated bypass / warn mode) ✅**
- **Actual**: The TC-07 script wrote the malformed row directly to:
  `lakehouse/bronze/streaming/op_trip_events/ingest_date=2026-06-17/tc07-bad-event.parquet`
- Row has `city_id = None`, `fare_total = "18.50"` (string), `event_id = "TC07-BAD-001-E1"`.
- This simulates the "warn mode" path — the event reached Bronze but was still bad.
- Fail condition: No visibility at all — the row should be traceable in Bronze even in warn mode.

**Step 3 — Silver quarantine routing ✅**
- **Actual**: Silver batch 7 (checkpoint `16:52 Jun 17`) produced:
  - **0 new files** in `silver/canonical_events/` — the bad event was NOT promoted.
  - **2 new files** in `silver/quarantine_events/` — the bad event was isolated.
- The `raw_payload` column in the quarantine parquet preserved the original JSON:
  ```json
  {"event_id": null, "trip_id": "TC07-BAD-001", "fare_amount": "18.50",
   "city_id": null, "rider_id": "RIDER-007", "driver_id": "DRIVER-007"}
  ```
- Fail condition: Any file written to `canonical_events` for this trip.

**Step 4 — Gold / Postgres / KPI mart clean ✅**
- **Actual**: All three queries returned 0:
  ```sql
  SELECT COUNT(*) FROM staging.silver_canonical_events WHERE trip_id='TC07-BAD-001';
  -- → 0

  SELECT COUNT(*) FROM gold.fact_trip WHERE trip_id='TC07-BAD-001';
  -- → 0

  SELECT COUNT(*) FROM gold.mart_city_daily_kpis WHERE city_id IS NULL;
  -- → 0
  ```
- `null` city never reached any fact table or the KPI mart.
- Fail condition: Any of the above returns > 0 — null propagation corrupted downstream.

**Verification commands**
```bash
# Check quarantine parquet content
python -c "
import pandas as pd, glob, os
files = sorted(glob.glob('lakehouse/silver/quarantine_events/*.parquet'), key=os.path.getmtime, reverse=True)[:5]
df = pd.concat([pd.read_parquet(f) for f in files])
print(df[df['trip_id']=='TC07-BAD-001'][['event_id','city_id','raw_payload']])
"

# Confirm absent from canonical and Gold
docker exec <postgres_container> psql -U ride_admin -d ride_warehouse -c \
  "SELECT COUNT(*) FROM staging.silver_canonical_events WHERE trip_id='TC07-BAD-001';"
```

**Pass criteria:**  
All 4 steps pass → malformed events are stopped at the contract gate (exit code 1), Silver routes them to quarantine preserving the raw payload, and zero null-city rows reach staging, Gold, or the KPI mart. The governance layer works as a real data quality control.

---

## TC-08 — Support Agent Asks the RAG Assistant a Refund Policy Question

**Business context:**  
A customer support agent needs to quickly find the correct refund policy for a rider who experienced a service disruption. Instead of searching through documents manually, they query the RAG assistant and expect a grounded, source-cited answer.

**Pre-conditions**
- Vector pipeline has run (`build_and_index_vectors.py` with `embedding.provider: ollama`). Weaviate `RideDocument` class is populated with **50 documents** (768-dim Ollama vectors) from 5 corpus sources.
- Ollama running with models: `nomic-embed-text` (embeddings) and `llama3.2:3b` (chat). Verify: `docker exec rh-ollama ollama list`.
- FastAPI `/api/v1/rag/ask` endpoint is reachable.
- The RAG endpoint uses real Ollama embeddings; `used_fallback` should be `false` on a healthy run.

**Test question**
> "What is the refund policy for a rider who experienced a service disruption due to a driver cancellation after pickup?"

**Steps and expected outcomes**

**Step 1 — Retrieval**
- Expected: The assistant retrieves ≥ 1 relevant document from Weaviate (`retrieved_count ≥ 1`). Retrieved documents contain policy-relevant text (refund, cancellation, disruption keywords).
- Fail condition: `retrieved_count = 0` — the vector index is empty or the query embedding failed.

**Step 2 — Answer grounding**
- Expected: The answer payload contains:
  - `answer`: a coherent policy statement, not an empty string.
  - `sources`: at least one source doc ID referencing the policy corpus.
  - `used_fallback`: preferably `false` (Ollama succeeded).
- Fail condition: `answer` is empty, or `sources` is empty (answer is hallucinated with no grounding).

**Step 3 — Answer accuracy (human review)**
- Expected: A human reviewer reads the `answer` and confirms it aligns with the content in the source document cited. The answer should mention refund eligibility or compensation for driver-cancelled post-pickup trips.
- Fail condition: Answer contradicts the source, gives a generic non-answer, or cites an unrelated document.

**Step 4 — API audit**
- Expected: `metadata.pipeline_run_audit` shows a `rag_assistant` run entry with `status = success` for this query.

**Pass criteria:**  
The support agent gets a grounded, accurate, source-cited answer in under 5 seconds. The platform delivers on its "AI-ready" promise.

---

## TC-09 — Demand Forecast Informs City Driver Supply Planning

**Business context:**  
The city operations team needs to know how many drivers to have online for the next day in Chicago. The demand forecasting model should produce a daily forecast per city that operations can act on (e.g., targeted driver incentives to boost supply in high-demand periods).

**Pre-conditions**
- At least 30 days of city-daily trip history in `gold.mart_city_daily_kpis`.
- Feature table `ml.feature_demand_city_daily` has been built.
- Demand model artifact (`ml/artifacts/demand_model.joblib`) exists.
- FastAPI `/api/v1/model/demand` is reachable.

**Test input (feature vector for next-day prediction)**

| Feature | Value |
|---------|-------|
| `city_id` | `CHI` |
| `day_of_week` | 5 (Saturday) |
| `month_of_year` | 6 |
| `is_holiday` | false |
| `trailing_7d_avg_trips` | 880 |
| `trailing_7d_avg_fare` | 19.50 |

**Steps and expected outcomes**

**Step 1 — Feature table**
- Expected: `ml.feature_demand_city_daily` has rows for `CHI` covering the last 30 days. `trailing_7d_avg_trips` is populated and non-zero.
- Fail condition: Feature table empty or all zeros — model would produce meaningless output.

**Step 2 — Demand model inference**
- Expected: `POST /api/v1/model/demand` returns `{"predicted_demand": ...}` with a value in a realistic range (e.g., 700–1,200 for a Saturday in a mid-size city).
- Fail condition: Prediction of 0, negative, or > 100,000 — model is not calibrated.

**Step 3 — Business interpretability**
- Expected: Saturday prediction is higher than the Tuesday equivalent (day_of_week = 2) for the same city and features. The model respects weekend demand patterns.
- Fail condition: Saturday and Tuesday produce identical forecasts — day-of-week feature is ignored.

**Step 4 — Forecast actionability**
- Expected: Output can be rounded to a driver headcount target (e.g., `predicted_demand / avg_trips_per_driver_per_day`). Operations can act on this number.

**Pass criteria:**  
The demand model produces realistic, day-of-week-aware forecasts that operations can translate directly into supply decisions.

---

## TC-11 — Operational Events Are Stored and Queryable in MongoDB

**Business context:**  
Fraud cases, rider app sessions, and support tickets are operational documents that need fast document-level access outside the warehouse. MongoDB serves as the operational store for these semi-structured events, synced from the Silver layer, and exposed through the FastAPI `/api/v1/ops/*` endpoints for support agents and trust-and-safety tooling.

**Pre-conditions**
- Silver canonical events populated (at least TC-01 through TC-05 executed).
- `scripts/sync_events_to_mongodb.py` has been run.
- MongoDB container `rh-mongodb` is healthy.
- FastAPI is running at `localhost:8000`.

**Test data (from prior TCs)**

| Collection | Expected document | Source TC |
|---|---|---|
| `fraud_cases` | `fraud_case_id=TC03-FRAUD-SIG-001B`, `risk_band=high`, `fraud_score=0.92` | TC-03 |
| `rider_app_sessions` | Sessions for TC01-RIDER-001, TC02-RIDER-001, TC03-RIDER-001, TC05-RIDER-001 | TC-01 to TC-05 |
| `support_tickets` | Created via POST (manual) | — |

**Steps and expected outcomes**

**Step 1 — Sync script**
- Run: `python scripts/sync_events_to_mongodb.py`
- Expected: Output reports upserted counts for `fraud_cases` and `rider_app_sessions`. No Python errors.
- Fail condition: `pymongo` import error or MongoDB connection refused.

**Step 2 — Fraud cases API**
- Expected: `GET /api/v1/ops/fraud-cases` returns `count >= 1` with TC-03 fraud document containing `risk_band=high`, `fraud_score=0.92`, `city_id=NYC`.
- Fail condition: Empty result or `count=0`.

**Step 3 — Rider sessions API**
- Expected: `GET /api/v1/ops/rider-sessions` returns `count >= 4`, one session per rider from TCs 01–05. Each session has `completion_rate`, `total_completions`, `event_time` populated.
- Fail condition: Missing sessions or null `completion_rate`.

**Step 4 — Support ticket create + read**
- Expected: `POST /api/v1/ops/support-tickets` with a valid payload returns `{"status": "created"}`. Subsequent `GET /api/v1/ops/support-tickets` returns the created ticket.
- Fail condition: 422 validation error or ticket not returned on GET.

**Step 5 — City filter**
- Expected: `GET /api/v1/ops/fraud-cases?city_id=NYC` returns only NYC fraud cases. `GET /api/v1/ops/rider-sessions?rider_id=TC01-RIDER-001` returns exactly 1 session.
- Fail condition: Filter ignored, all records returned regardless of city/rider.

**Pass criteria:**  
Operational events flow from Silver into MongoDB and are accessible through typed API endpoints. Support agents and trust-and-safety tools can query documents without touching the warehouse.

---

## TC-12 — Grafana Dashboard Shows Live KPIs from the Warehouse

**Business context:**  
The city operations team opens Grafana each morning to review trip volumes, fare totals, surge multipliers, and platform health. The dashboard must load without errors, show current data from PostgreSQL, and display accurate KPIs matching direct warehouse queries.

**Pre-conditions**
- Grafana container `rh-grafana` is running (`localhost:3000`). Login: `admin` / `admin`.
- Grafana is on **both** `monitoring_net` and `platform_core_net` — required so Grafana can reach the `rh-postgres` container on the platform network.
- Two datasources auto-provisioned via `docker/grafana/provisioning/datasources/datasource.yml`:
  - **PostgreSQL** (`uid: ${DS_POSTGRESQL}`) → `postgres:5432`, db `ride_warehouse`, user `ride_admin`
  - **Prometheus** (`uid: ${DS_PROMETHEUS}`) → `http://prometheus:9090`
- Dashboard auto-provisioned via `docker/grafana/provisioning/dashboards/ride_hailing_kpis.json`.
- `gold.mart_city_daily_kpis` has at least one row (populated by `dbt run`).
- `metadata.pipeline_run_audit` has rows (written by all audited pipeline scripts).
- `metadata.data_quality_audit` has rows — run `python scripts/monitor_data_quality.py` to populate.

**Dashboard layout (8 sections, 12 panels)**

| Panel | Type | Data source | SQL / query |
|---|---|---|---|
| City Daily KPIs | Table | PostgreSQL | `gold.mart_city_daily_kpis` — all dates, all cities |
| Completed Trips Over Time by City | Time series | PostgreSQL | `event_date`, `city_id`, `completed_trips` |
| Gross Fare Total Over Time by City | Time series (USD) | PostgreSQL | `event_date`, `city_id`, `gross_fare_total` |
| Current Avg Surge Multiplier by City | Stat (colour thresholds ≥1.3=yellow, ≥1.8=red) | PostgreSQL | Latest `event_date` only |
| Driver Payout Today by City | Stat (blue, USD) | PostgreSQL | Latest `event_date` only |
| Platform Revenue Today by City | Stat (purple, USD) | PostgreSQL | Latest `event_date` only |
| Completed Trips Today by City | Stat (green) | PostgreSQL | Latest `event_date` only |
| Recent Pipeline Runs | Table | PostgreSQL | `metadata.pipeline_run_audit` — last 20, with `stage_name`, `duration_seconds` from JSONB |
| Data Quality Audit Results | Table | PostgreSQL | `metadata.data_quality_audit` — last 20, with `rule_id`, `violation_count` |
| Service Up/Down | Stat (UP/DOWN badge) | Prometheus | `up` metric |
| FastAPI Request Rate (req/s) | Time series | Prometheus | `rate(fastapi_requests_total[1m])` |
| FastAPI p95 Latency | Time series (s) | Prometheus | `histogram_quantile(0.95, ...)` |

**Steps and expected outcomes**

**Step 1 — Dashboard visible**
- Navigate to `http://localhost:3000` → Dashboards → **Ride-Hailing Platform KPIs**.
- Expected: Dashboard loads. All 12 panels render — no "No data" on KPI panels, no `db query error: failed to connect to server`.
- Troubleshooting: If PostgreSQL panels show connection error, run `docker network connect platform_core_net rh-grafana` to reconnect Grafana to the platform network.
- Fail condition: Any panel shows `db query error` — Grafana cannot reach PostgreSQL (network isolation issue).

**Step 2 — City KPIs table panel (Panel 1)**
- Expected: Table shows rows for all active cities (`NYC`, `CHI`, `DXB`, `MIA`) with `event_date = 2026-06-16`. Columns visible:
  - `City`, `Date`, `Completed Trips`, `Cancelled Trips`, `gross_fare_total` (USD formatted), `Platform Fee ($)`, `Driver Payout ($)`, `avg_surge_multiplier`
- Verify against DB:
  ```sql
  SELECT city_id, event_date, completed_trips, ROUND(gross_fare_total::numeric, 2)
  FROM gold.mart_city_daily_kpis ORDER BY event_date DESC, city_id;
  ```
- Fail condition: Panel empty, or values differ from direct SQL — indicates a stale materialized view or dbt hasn't run.

**Step 3 — Time series panels (Panels 2–3)**
- Expected: **Completed Trips Over Time** and **Gross Fare Total Over Time** each show one line per city across 7 days (June 10–16). June 16 shows the highest volume (bulk run day). Each city uses a distinct colour.
- Fail condition: Only one date visible — historical data not seeded, or dbt ran incrementally and skipped older rows.

**Step 4 — Stat panels — today's snapshot (Panels 4–7)**
- Expected: All four stat panels show non-zero values for the latest date:
  - **Current Avg Surge Multiplier by City**: CHI ≈ 1.15 (yellow), NYC ≈ 1.05 (green)
  - **Driver Payout Today**: NYC ≈ $6,040, CHI ≈ $3,767, DXB ≈ $3,389, MIA ≈ $1,619
  - **Platform Revenue Today**: NYC ≈ $1,990, CHI ≈ $1,256, DXB ≈ $1,130, MIA ≈ $540
  - **Completed Trips Today**: NYC 83, CHI 71, DXB 40, MIA 30 (values match bulk run output)
- Fail condition: Any stat shows `0` or `No data` — the mart hasn't been populated or dbt skipped the latest batch.

**Step 5 — Recent Pipeline Runs panel (Panel 8)**
- Expected: The **Recent Pipeline Runs** table shows the last 20 audit records from `metadata.pipeline_run_audit`, with columns:
  - `Started` (timestamp), `Pipeline`, `Stage`, `status` (green SUCCESS / red FAILED), `Ended`, `Duration (s)`
  - Most recent entries should include: `vector_index_builder`, `ml_train_*`, `airflow_dbt_transform`, `kafka_to_postgres_loader`
- Verify against DB:
  ```sql
  SELECT pipeline_name, stage_name, status, started_at, ended_at,
         details->>'duration_seconds' AS duration_s
  FROM metadata.pipeline_run_audit ORDER BY started_at DESC LIMIT 5;
  ```
- Fail condition: Table empty — indicates the SQL used the wrong column names (`records_processed`, `completed_at` are not valid columns; the correct columns are `details` JSONB and `ended_at`).

**Step 6 — Data Quality Audit Results panel (Panel 9)**
- Expected: The **Data Quality Audit Results** table shows the last 20 DQ check results from `metadata.data_quality_audit`, with columns:
  - `Checked At`, `run_id`, `Rule` (e.g., `kpi_table_not_empty`, `kpi_table_freshness`, `kpi_negative_fares`), `Target`, `status` (green PASSED / red FAILED), `Violations`
  - Most recent run should show all three rules as PASSED with `violation_count = 0`.
- Populate fresh entries by running: `python scripts/monitor_data_quality.py`
- Verify against DB:
  ```sql
  SELECT rule_id, target_entity, status, violation_count, observed_at
  FROM metadata.data_quality_audit ORDER BY observed_at DESC LIMIT 6;
  ```
- Fail condition: Table empty — DQ monitor has never been run, or the SQL referenced `data_quality_results` (incorrect table name).

**Step 7 — Prometheus health panels (Panels 10–12)**
- Expected:
  - **Service Up/Down**: `UP` badges (green) for `fastapi`, `prometheus`, `cadvisor`, `node-exporter`; `spark-master` may show if Spark scrape target is configured.
  - **FastAPI Request Rate**: non-zero line after sending at least one API request to `localhost:8000`.
  - **FastAPI p95 Latency**: shows a latency trace; RAG and ML inference endpoints will be the highest (typically 0.5–3 s).
- Fail condition: All services `DOWN` — Prometheus datasource not connected, or scrape targets misconfigured.

**Step 8 — Data consistency cross-check**
- Expected: The `gross_fare_total` for NYC on 2026-06-16 shown in Panel 1 matches the value returned by:
  ```bash
  curl "http://localhost:8000/api/v1/analytics/city-daily?city_id=NYC"
  ```
- Both sources query PostgreSQL — values must be identical.
- Fail condition: Values differ — API applies a filter or aggregation that differs from the Grafana SQL.

**Pass criteria:**  
All 8 steps pass. The Grafana dashboard loads fully, all 12 panels display data, the Pipeline Audit and Data Quality panels show live rows from `metadata` schema, and KPI values are consistent with direct warehouse queries and the API.

---

## TC-10 — Pipeline Failure is Detected and Surfaced in Observability

**Business context:**  
The ML feature pipeline fails overnight due to missing source data. The platform's observability layer must detect the failure, record it in the audit trail, and surface it in Prometheus/Grafana so the on-call engineer is alerted before the morning dashboard review.

**Pre-conditions**
- Prometheus and Grafana are running.
- `metadata.pipeline_run_audit` table exists.
- Alert rules in `docker/prometheus/alerts.yml` are active.
- Simulate failure by running the feature pipeline with no source data (empty `gold.mart_city_daily_kpis`).

**Simulated failure scenario**
- Truncate `gold.mart_city_daily_kpis` (test environment only).
- Run `python ml/feature_pipeline/build_feature_tables.py`.

**Steps and expected outcomes**

**Step 1 — Pipeline audit record**
- Expected: `metadata.pipeline_run_audit` contains a row for `build_feature_tables` with `status = failed`, a non-null `ended_at`, and a `details` JSON field describing the error (e.g., `"source_rows": 0`).
- Fail condition: No audit row written — the failure is invisible.

**Step 2 — API observability endpoint**
- Expected: `GET /api/v1/monitoring/pipeline-runs/latest` returns the failed run at the top of the list with `status = failed`.
- Fail condition: Failed run absent or shown as `success`.

**Step 3 — Data quality audit**
- Expected: Running `python scripts/monitor_data_quality.py` after the failure records a `failed` row in `metadata.data_quality_audit` for the freshness check (mart is now empty/stale).
- Fail condition: DQ check reports `passed` — the empty table is not caught.

**Step 4 — Prometheus alert fires**
- Expected: The `FastAPIHighErrorRate` or a data-quality alert is visible in `http://localhost:9090/alerts` as `FIRING`. Grafana surfaces this on the operations dashboard.
- Fail condition: No alert fires — the on-call engineer has no signal.

**Pass criteria:**  
A pipeline failure is fully visible within minutes: audit trail, API endpoint, DQ check, and Prometheus alert all reflect the failure state. The on-call engineer can act before business users notice.

---

## Validation Checklist

Use this table to track walkthrough results. For each test case, record the outcome at each layer.

| TC | Bronze | Silver | Gold / Warehouse | ML / RAG | API | Observability | Overall |
|----|--------|--------|-----------------|----------|-----|---------------|---------|
| TC-01 | ✅ | ✅ | ✅ | — | ✅ | — | ✅ |
| TC-02 | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| TC-03 | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| TC-04 | — | — | ✅ | ✅ | ✅ | — | ✅ |
| TC-05 | ✅ | ✅ | ✅ | — | — | — | ✅ |
| TC-06 | — | — | ✅ | — | ✅ | ✅ | ✅ |
| TC-07 | ✅ | ✅ | ✅ | — | — | — | ✅ |
| TC-08 | — | — | — | ✅ | ✅ | — | ✅ |
| TC-09 | — | — | ⬜ | ⬜ | ⬜ | — | ⬜ |
| TC-10 | — | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| TC-11 | — | ✅ | — | — | ✅ | — | ✅ |
| TC-12 | — | — | ✅ | — | ✅ | ✅ | ✅ |

Legend: ⬜ not yet validated · ✅ pass · ❌ fail · — not applicable for this layer

---

## Notes

- All test cases use synthetic data unless otherwise noted. No real rider/driver PII is involved.
- Test cases TC-01 through TC-06 should be run in sequence on a clean pipeline run to establish baseline data.
- TC-07 should be run in a separate isolated pipeline session to avoid corrupting clean data.
- TC-10 should always be run last and the source table restored immediately after validation.
- Revisit this document after any schema change, new city activation, or major pipeline refactor.
