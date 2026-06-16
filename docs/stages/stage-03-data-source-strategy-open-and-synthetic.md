# Stage 3 - Data Source Strategy (Open + Synthetic Ride Data)

## 1) Stage objective

Stage 3 defines a production-grade data sourcing strategy for the ride-hailing platform.

Goals:
- Use high-quality open datasets where available
- Fill enterprise gaps using realistic synthetic generation
- Ensure all required ride-hailing domains are represented
- Keep data contracts, quality controls, and lineage from day one
- Make datasets directly usable for streaming, lakehouse, warehouse, ML, and vector use cases

This is a strategy and design stage. Implementation of ingestion/simulation begins in later stages.

---

## 2) Why open data alone is not enough

Public taxi datasets are excellent for trip-level analytics but usually do not include full enterprise ride-hailing signals:
- Real-time app event streams
- Driver online/offline and acceptance behavior
- Promotion redemption and incentive eligibility
- Fraud telemetry and support investigation trails
- Payment gateway lifecycle states
- Customer support case logs with resolution lifecycle

Therefore, the correct enterprise strategy is:
- Use open datasets for realistic trip and geospatial baselines
- Layer synthetic event generation for missing operational and AI-critical domains

---

## 3) Candidate open datasets and enterprise suitability

## 3.1 NYC TLC Trip Record Data
Use for:
- Trip lifecycle approximations (pickup/dropoff timestamps)
- Fare components and trip economics
- Spatial demand patterns by zones and times
- Baseline demand forecasting training

Limitations:
- No direct rider/driver app behavior
- No incentives/promo decision trails
- No support/fraud case narratives

## 3.2 Chicago Taxi Trips
Use for:
- Additional city pattern diversity
- Multi-city generalization testing
- Zone-level demand and fare behavior

Limitations:
- Similar to NYC: limited operational micro-events

## 3.3 Optional enrichment datasets (if needed)
- Open weather and event calendars (for demand features)
- Public holidays per city/region
- Open geospatial boundary files

Note: External enrichments are optional and can be synthetic for offline local runs.

---

## 4) Source taxonomy for this platform

Define data sources as four classes:

1. Open historical datasets
   - NYC/Chicago taxi-style batch datasets
2. Synthetic operational event streams
   - Rider app, driver location, dispatch, pricing, payment, fraud, support
3. Synthetic master/reference dimensions
   - Riders, drivers, vehicles, cities, promotions, payment methods
4. Synthetic text corpora for vector/RAG
   - Reviews, support tickets, policy docs, fraud case notes, FAQ documents

This taxonomy allows complete coverage of required platform domains.

---

## 5) Required domain coverage mapping (must-have)

The platform must include all required domains; below is source strategy mapping.

1. Real-time ride events -> synthetic streaming + open-derived templates
2. Driver location streaming -> synthetic telemetry
3. Rider app events -> synthetic clickstream/session events
4. Trip lifecycle tracking -> open + synthetic event decomposition
5. Payment processing -> synthetic transaction lifecycle events
6. Surge pricing logic -> synthetic pricing signal stream + demand/supply features
7. Discounts and promotions -> synthetic promotion campaign and redemption events
8. Refunds -> synthetic post-payment adjustment events
9. Ratings and reviews -> synthetic structured scores + text reviews
10. Driver earnings -> synthetic earning ledger from trip and incentive policies
11. Incentives -> synthetic policy engine outputs
12. Fraud signals -> synthetic rules/anomaly events with labels
13. Customer support logs -> synthetic ticket lifecycle + text corpus
14. Geo-location data -> open zone maps + synthetic pings
15. City-level aggregation -> open + synthetic multi-city parameterization
16. Revenue, margin, platform fee -> derived synthetic financial facts from trip/payment layers

---

## 6) Synthetic data design principles (enterprise-grade)

## 6.1 Realism principles
- Preserve realistic temporal demand curves (peak commute, weekends, events)
- Preserve city-specific geospatial traffic patterns
- Maintain coherent trip economics (distance, duration, fare, surge, discount)
- Enforce causal consistency across events

## 6.2 Referential integrity
- Every event links to valid entity keys (trip_id, rider_id, driver_id, city_id)
- State transitions must follow allowed lifecycle rules
- Payment and refund events must reconcile to trip/payment IDs

## 6.3 Distribution design
- Heavy-tail behavior for certain metrics (wait time, earnings outliers)
- Seasonality and periodicity signals for forecasting
- Controlled class imbalance for fraud labels

## 6.4 Reproducibility
- Seeded generation for deterministic reruns
- Versioned generator profiles by city and scenario
- Metadata capture of generator parameters per run

---

## 7) Synthetic generation architecture blueprint

## 7.1 Generator components
- Master data generator (rider, driver, vehicle, city, promotions)
- Event simulator (trip lifecycle, app events, dispatch events)
- Financial simulator (payment, refunds, payouts, fees)
- Risk/support text generator (fraud cases, tickets, reviews)
- Scenario engine (spikes, weather disruption, event-day anomalies)

## 7.2 Execution modes
- Batch bootstrap mode: generate baseline historical data
- Streaming mode: emit near-real-time events to Kafka topics
- Replay mode: regenerate historical windows for testing backfills

## 7.3 Output targets
- CSV/Parquet bootstrap files for initial lakehouse load
- Kafka topic producers for live simulation
- JSONL text corpora for embedding pipelines

---

## 8) Open-data-to-event decomposition strategy

Open taxi datasets are often trip-level rows, not event streams. For platform realism:
- Convert each trip row into a sequence of lifecycle events
- Infer event timestamps from pickup/dropoff plus modeled offsets
- Generate associated operational side events:
  - rider app request
  - driver assignment and ETA updates
  - payment authorization/capture
  - optional review and support outcomes

This allows open historical data to feed streaming architecture tests.

---

## 9) Data contracts for source ingestion

Every source (open or synthetic) must publish against a contract with:
- dataset_or_topic_name
- domain
- schema_version
- business_key fields
- event_time field
- PII classification
- required quality rules
- retention policy
- owner team

Contract enforcement points:
- Pre-ingestion validation for batch files
- Consumer-side schema validation for streams
- Drift quarantine for violating records

---

## 10) Data quality framework at source stage

## 10.1 Structural checks
- Required columns present
- Data types valid
- Enum values in allowed set

## 10.2 Referential checks
- Foreign keys resolve to dimension candidates
- No orphan trip/payment/refund links

## 10.3 Business checks
- pickup_time <= dropoff_time
- fare_total >= 0
- surge_multiplier within policy bounds
- platform_fee + driver_payout + taxes + discounts reconciles to total fare logic

## 10.4 Statistical checks
- Volume thresholds by city/hour
- Null/outlier drift detection
- Fraud label distribution monitoring

---

## 11) PII, privacy, and synthetic-safe design

For local enterprise simulation:
- Do not use raw personal identifiers from open data
- Generate pseudonymous rider/driver identities
- Mask or tokenize any potentially sensitive fields
- Maintain data-classification tags in metadata

Synthetic text corpora rules:
- No real personal names required
- Use policy-safe templates for support/fraud narratives

---

## 12) Source-level lineage strategy

Record lineage fields from source stage onward:
- source_system
- source_file_or_topic
- source_record_id
- ingestion_run_id
- generator_profile_version
- contract_version
- ingest_timestamp

Lineage enables:
- Replay and audit
- Root-cause analysis for DQ failures
- ML experiment reproducibility

---

## 13) SLA design for source pipelines

Define source SLAs by class:

P0 streams (trip, payment, fraud):
- Freshness target: near real-time (minutes)
- Contract compliance target: very high (strict)

P1 streams (app events, location, support):
- Freshness: low-latency, slightly relaxed

Batch bootstrap/open loads:
- Completeness and reconciliation-focused SLA

Additional SLA dimensions:
- Schema conformance rate
- Source ingest success rate
- Quarantine rate threshold

---

## 14) Scalability strategy for source layer

Support millions of rides/day by design:
- Shard synthetic generation by city and time windows
- Parallel producer workers per topic partition
- Separate high-volume telemetry streams (driver_location)
- Use bounded payload sizes and compression where appropriate
- Implement backpressure-aware producer settings

Batch scaling:
- Partition source files by date/city
- Incremental append ingestion
- Avoid full reloads except controlled bootstrap

---

## 15) Cost optimization at source stage

- Generate only required domains for current stage/tests
- Parameterize event rates by city tier
- Keep raw retention in compressed formats
- Use sampled subsets for local experimentation while preserving realistic distributions
- Use synthetic profiles (small/medium/enterprise scale) for controlled test budgets

---

## 16) Enterprise folder structure for Stage 3 artifacts

Target additions:

- data_sources/open/
  - nyc_taxi/
  - chicago_taxi/
- data_sources/synthetic/
  - profiles/
  - generators/
  - scenarios/
- contracts/sources/
- config/source_catalog/
- docs/data-catalog/

Purpose:
- Keep source definitions, profiles, and contracts discoverable and versioned

---

## 17) Metadata-driven source catalog design

Create source catalog entries with fields:
- source_id
- source_type (open_batch, synthetic_batch, synthetic_stream, text_corpus)
- domain
- schema_ref
- expected_grain
- partition_columns
- pii_level
- quality_rule_set
- ingestion_mode
- target_bronze_table
- owner
- active_flag

Runtime behavior:
- Ingestion engine reads catalog and loads/enqueues sources dynamically
- New source onboarding mainly via metadata, not code changes

---

## 18) How Uber-like companies handle source strategy

Typical enterprise pattern:
- Historical external data for baseline demand/spatial patterns
- Rich internal event telemetry for operational truth
- Simulation/sandbox datasets for testing and incident drills
- Strict contracts and quality gates at ingestion boundary
- Source ownership split by domain teams with platform governance

Key insight:
The competitive advantage is not only volume, but reliable and semantically consistent source coverage across all operational touchpoints.

---

## 19) Azure migration equivalence for source strategy

Open-source local design -> Azure equivalent:
- Kafka stream ingestion -> Event Hubs
- Spark ingestion/standardization -> Azure Databricks
- Lakehouse raw landing -> ADLS Gen2 + Delta
- Source metadata catalog -> Azure SQL / Databricks tables
- Data quality monitoring -> Azure Monitor + custom DQ dashboards
- Vector text corpora staging -> ADLS + Azure AI Search indexing pipeline

Migration principle:
Keep source contracts and generator metadata cloud-neutral; swap transport/storage adapters by environment.

---

## 20) Step-by-step implementation plan (Stage 3 scope)

1. Confirm open dataset shortlist and download strategy.
2. Define source catalog schema (metadata-driven).
3. Define contract templates for batch and stream sources.
4. Design synthetic generator profiles (small/medium/enterprise).
5. Define event decomposition rules for trip-level open data.
6. Define DQ rule catalog and quarantine strategy.
7. Define lineage fields and run metadata conventions.
8. Finalize source folder and config standards for implementation stages.

---

## 21) Interview-ready talking points

- Open data gives realism for trip economics and spatiotemporal demand, but cannot represent full operational telemetry.
- Enterprise-grade source strategy combines open baselines with contract-driven synthetic event generation.
- Metadata-driven source catalogs are essential for scaling to multiple cities/domains with low code churn.
- Source-level data quality and lineage prevent downstream instability in analytics and AI models.

---

## 22) Stage 3 exit criteria

Stage 3 is complete when:
- Open vs synthetic source strategy is approved per domain.
- All 16 required ride-hailing data domains are mapped to concrete sources.
- Source contracts and quality rule patterns are defined.
- Source metadata catalog structure is finalized.
- Scalability, SLA, and lineage strategy are documented.
- Azure-equivalent source architecture is documented.

---

## 23) Alignment artifacts created in this stage

To guarantee that open datasets (NYC/Chicago) and synthetic streams remain aligned as one platform data model, the following artifacts are the source of truth:

- `config/source_catalog/canonical_alignment.yaml`
   - Canonical trip-event contract
   - Per-source mappings (NYC, Chicago, synthetic)
   - Alignment validation rules
   - Required domain coverage list

- `docs/standards/open-synthetic-alignment-standard.md`
   - Enterprise alignment policy
   - Normalization decisions
   - Enforcement plan for Stage 6/7 runtime pipelines

These artifacts make alignment explicit and auditable before implementation.
