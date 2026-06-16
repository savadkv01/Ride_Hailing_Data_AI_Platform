# Stage 6 - Kafka Ingestion & Event Simulation

## 1) Stage objective

Stage 6 operationalizes the event backbone for the ride-hailing platform:
- Standardize ingestion into Kafka for open and synthetic sources
- Implement contract-aligned event simulation across all required domains
- Ensure replayability, observability, and scale-ready topic design
- Prepare reliable handoff to Stage 7 Spark Structured Streaming

This stage translates source strategy and data modeling into executable event pipelines.

---

## 2) Why this stage matters

In Uber-like platforms, event streams are the control plane of the data platform. If event ingestion is inconsistent, every downstream layer (Bronze/Silver/Gold, warehouse, ML, RAG) becomes unreliable.

Stage 6 guarantees:
- Deterministic event contracts
- Domain-complete stream coverage
- Repeatable simulation for testing and backfills
- Operational confidence for real-time processing

---

## 3) Ingestion architecture (Stage 6)

## 3.1 Source classes
1. Open batch sources
   - NYC TLC trips
   - Chicago taxi trips
2. Synthetic streaming sources
   - All operational and financial domains required by platform scope

## 3.2 Ingestion path
Open/Synthetic Source -> Contract Mapping -> Kafka Topic -> Consumer Groups (Stage 7 onward)

## 3.3 Current implementation state
- Open-source download and normalization scripts: implemented
- Per-domain synthetic generator scripts: implemented
- Catalog-driven Kafka producer runner: implemented
- Multi-source producer manager from source index: implemented

---

## 4) Kafka topic taxonomy and domain mapping

## 4.1 Topic naming convention
`rh.<domain>.<entity>.<event>.v<version>`

## 4.2 Required domain topics (implemented)
- rh.trip.lifecycle.events.v1
- rh.driver.location.pings.v1
- rh.rider.app.events.v1
- rh.payment.transactions.v1
- rh.pricing.surge.signals.v1
- rh.promotion.events.v1
- rh.refund.events.v1
- rh.review.events.v1
- rh.earnings.events.v1
- rh.incentive.events.v1
- rh.fraud.signals.v1
- rh.support.tickets.v1
- rh.geo.events.v1
- rh.city.agg.events.v1
- rh.revenue.margin.events.v1

## 4.3 Topic configuration baseline
- Partitions: 6 (local baseline)
- Replication factor: 1 (local)
- Auto-create topics: disabled
- Retention: domain policy driven (local default configured)

---

## 5) Data contracts and schema governance

## 5.1 Contract-first ingestion
Each source domain is cataloged with:
- source_id
- kafka_topic
- generator_script
- contract_version
- key_fields
- watermark_column
- city_scope

## 5.2 Contract assets
- `config/source_catalog/source_catalog_index.yaml`
- `config/source_catalog/synthetic/*.yaml`
- `config/source_catalog/open/*.yaml`
- `config/source_catalog/canonical_alignment.yaml`

## 5.3 Schema evolution policy
- Additive optional fields: allowed in minor versions
- Breaking changes: new versioned topic or explicit migration window
- Contract mismatch handling: quarantine pattern (to be implemented in Stage 7 DQ path)

---

## 6) Open data ingestion design (implemented)

## 6.1 Sources from strategy
- NYC TLC trip data
- Chicago taxi trip data

## 6.2 Open ingestion flow
Download raw -> Bronze Open landing -> Normalize to canonical `op_trip_events` schema -> publish-ready for Kafka/Spark

## 6.3 Implemented scripts
- `ingestion/open_data/download_nyc_tlc.py`
- `ingestion/open_data/download_chicago_taxi.py`
- `ingestion/open_data/normalize_nyc_to_canonical.py`
- `ingestion/open_data/normalize_chicago_to_canonical.py`

## 6.4 Canonicalization behavior
- Pseudonymous rider/driver IDs for open data
- Consistent `event_id`, `trip_id`, `city_id`, `event_time`, monetary fields
- Alignment references from canonical mapping config

---

## 7) Synthetic event simulation design (implemented)

## 7.1 Per-domain generator model
Each required synthetic domain has a separate generator script (one file per dataset) for maintainability and ownership.

## 7.2 Implemented generator set
- generate_trip_events.py
- generate_driver_location_events.py
- generate_rider_app_events.py
- generate_payment_events.py
- generate_surge_pricing_events.py
- generate_promotion_events.py
- generate_refund_events.py
- generate_review_events.py
- generate_driver_earnings_events.py
- generate_incentive_events.py
- generate_fraud_signal_events.py
- generate_support_ticket_events.py
- generate_geo_events.py
- generate_city_agg_events.py
- generate_revenue_margin_events.py

## 7.3 Shared generator utilities
- `ingestion/synthetic/common.py`
- City-aware generation and ID utilities

---

## 8) Metadata-driven producer orchestration (implemented)

## 8.1 Single-source producer runner
- `ingestion/synthetic/producer_runner.py`
- Reads one source config YAML and emits events to configured topic

## 8.2 Multi-source catalog manager
- `ingestion/synthetic/catalog_producer_manager.py`
- Reads `source_catalog_index.yaml`
- Starts producer processes for all synthetic sources

## 8.3 Runtime controls
- `--bootstrap-servers`
- `--events-per-second`
- `--max-events` (bounded test runs vs continuous streaming)

---

## 9) Stage 6 runtime validation (executed)

Validation steps completed:
1. Project venv activated and Python environment validated
2. Kafka container started successfully
3. Required topics created/verified
4. Catalog manager executed across all synthetic domains
5. Topic offsets verified (events landed per domain)

Result:
- End-to-end synthetic ingestion run completed with successful per-topic event writes.

---

## 10) Observability and logging for ingestion

## 10.1 Producer logs
- Source ID, topic, module, bootstrap target
- Sent event counts
- Failure traceback for fast triage

## 10.2 Ingestion monitoring metrics (target)
- Events produced/sec per topic
- Producer failure rate
- Kafka topic lag by consumer group (Stage 7 consumers)
- End-to-end publish latency

## 10.3 Alerting patterns
- Topic no-data windows for critical domains
- Producer crash loops
- Event throughput anomalies by city

---

## 11) Scalability design (millions of rides/day)

## 11.1 Partitioning strategy
- Partition keys by high-cardinality stable IDs where ordering matters
- Separate high-volume domains (driver location, rider app events)

## 11.2 Producer scaling
- Multi-process producers by domain/city
- Adjustable event rates via CLI and profiles
- Burst simulation for incident and load testing

## 11.3 Backpressure handling
- Bounded producer send retries
- Tunable linger and batch behavior
- Consumer lag monitoring and scaling in Stage 7

---

## 12) Cost and efficiency controls

- Use bounded test mode (`--max-events`) during development
- Domain-specific rate controls to avoid unnecessary load
- Reuse source catalog metadata instead of per-script hardcoding
- Keep simulation deterministic via profile-based runs (future extension)

---

## 13) Security and governance controls

- No real PII in synthetic generators
- Pseudonymized open-source derived identities
- Explicit source ownership in catalog
- Versioned contract references in metadata

---

## 14) Enterprise implementation pattern (Uber-like)

Typical pattern:
- Strict domain event contracts managed by platform governance
- Independent producer services and replay-capable event logs
- Synthetic simulation frameworks for testing reliability and incident drills
- Catalog-driven onboarding to reduce code churn as domains/cities grow

---

## 15) Azure migration equivalence (Stage 6)

- Kafka topics -> Event Hubs entities/partitions
- Python producers -> Event producer clients / Databricks jobs
- Source catalog YAML -> Azure SQL/Databricks metadata tables
- Local ingestion logs -> Azure Monitor + Log Analytics

Migration principle:
Keep contracts, topic semantics, and event keys stable while replacing transport runtime.

---

## 16) File map for Stage 6 implementation

Key implemented files:
- `config/source_catalog/source_catalog_index.yaml`
- `config/source_catalog/open/*.yaml`
- `config/source_catalog/synthetic/*.yaml`
- `ingestion/open_data/*.py`
- `ingestion/synthetic/common.py`
- `ingestion/synthetic/generate_*.py`
- `ingestion/synthetic/producer_runner.py`
- `ingestion/synthetic/catalog_producer_manager.py`
- `docker/kafka/topics-bootstrap.sh`

---

## 17) Step-by-step runbook (current)

1. Start Kafka from compose stack.
2. Bootstrap topics.
3. Run single producer for focused testing or catalog manager for full-domain tests.
4. Verify topic offsets and producer logs.
5. Persist run metadata into audit store (next enhancement).

---

## 18) Stage 6 exit criteria

Stage 6 is complete when:
- All required ingestion domains have topic mappings and source configs.
- Separate synthetic dataset files exist per domain.
- Open data sources are ingested and normalized into canonical schema.
- Catalog-driven producer orchestration runs successfully.
- Kafka topic writes are verified for all required domains.
- Stage 7 can consume streams from stable, contract-aligned topics.
