# Source vs Data Model Coverage Audit

Date: 2026-03-02

## Scope
Validation of alignment between:
- Stage 3 source strategy
- Stage 4 operational data model
- Source catalog metadata
- Open normalization scripts
- Synthetic generator payload columns

## Summary Status
- Source domain coverage: Complete
- Column-level coverage: Complete for Stage 6 operational ingestion scope
- Recommendation before Stage 7 productionization: proceed with Spark contract enforcement and DQ checks

## 1) Source coverage check

### 1.1 Open sources
Present:
- NYC TLC source config
- Chicago Taxi source config

Result: OK

### 1.2 Synthetic domains
Present as separate files (one per dataset):
- trip_lifecycle_tracking
- driver_location_streaming
- rider_app_events
- payment_processing
- surge_pricing
- discounts_and_promotions
- refunds
- ratings_reviews
- driver_earnings
- incentives
- fraud_signals
- customer_support_logs
- geo_location_data
- city_level_aggregation
- revenue_margin_platform_fee

Result: OK for listed domains

### 1.3 Additional strategy-required entries
Added as explicit source entries:
- real_time_ride_events
- synthetic master/reference dimensions (rider/driver/vehicle/city/promotion/payment method)
- synthetic vector text corpora (reviews/support/policy/faq/fraud cases)

Result: OK

## 2) Canonical trip schema coverage check

Required by canonical alignment for trip events includes:
- pickup_ts, dropoff_ts
- pickup_lat, pickup_lng, dropoff_lat, dropoff_lng
- distance_km, duration_sec

Observed in open normalizers:
- NYC and Chicago normalizers now include required canonical fields:
  - pickup_ts, dropoff_ts
  - pickup_lat, pickup_lng, dropoff_lat, dropoff_lng
  - distance_km, duration_sec

Result: OK

## 3) Synthetic generator column coverage vs operational ERD

Hardening completed:
- `generate_trip_events.py` now includes ingestion and financial contract fields.
- `generate_driver_location_events.py` now includes speed, bearing, online status.
- `generate_rider_app_events.py` now includes app_version.
- `generate_payment_events.py` now includes gateway_ref and method_code.
- All synthetic generators now include `source_system`.

Result: OK

## 4) Final confirmation

Can we confirm everything is fully aligned right now?
- Source presence: Yes
- Columns aligned to Stage 4 operational model + Stage 3 source strategy for ingestion scope: Yes

Overall status: Alignment complete for Stage 6 ingestion scope.

## 5) Remaining recommendations before full Stage 7 contract enforcement

1. Add runtime schema validation against catalog contracts in Spark ingestion.
2. Add DQ rule execution and quarantine outputs for malformed events.
3. Add audit persistence for per-source ingestion run metadata.
4. Add integration test that checks payload keys against source catalog contract per topic.

## 6) Suggested next action

Proceed to Stage 7 and enforce these aligned contracts in Bronze/Silver streaming pipelines.
