# Stage 0 - Business Context & Ride-Hailing Domain Modeling

## 1) Why this stage exists

Stage 0 defines the business truth of the platform before any technical implementation. In enterprise ride-hailing systems, most failures in data and AI programs come from ambiguous domain definitions, inconsistent metrics, and unclear ownership between product, operations, finance, and data teams.

This stage establishes:
- Common business vocabulary
- KPI definitions with calculation rules
- Ride lifecycle and event boundaries
- Domain ownership and service boundaries
- Non-functional expectations (SLA, scale, governance)

Without this, downstream architecture, data contracts, feature engineering, and model outputs become inconsistent and non-trustworthy.

---

## 2) Uber-like business operating model (enterprise view)

### Core value chain
1. Rider demand creation (search, quote, request)
2. Supply matching (driver availability + ETA + acceptance)
3. Trip fulfillment (pickup to dropoff)
4. Monetary settlement (fare, fees, tax, payout)
5. Post-trip trust loop (ratings, support, fraud actions)

### Business levers
- Growth: active riders, active drivers, city activation
- Efficiency: matching speed, pickup ETA, cancellation ratio
- Profitability: take rate, contribution margin, incentive burn
- Reliability: completion rate, on-time pickup, app/API uptime
- Trust & safety: fraud rate, incident response, support resolution

### Key personas
- Rider
- Driver/partner
- Operations manager (city/regional)
- Finance & revenue assurance
- Trust and safety analysts
- Customer support agents
- Data engineering / ML engineering teams

---

## 3) Domain boundaries (microservices vs data platform)

## Operational microservices (source-of-truth at transaction time)
- Rider service
- Driver service
- Trip orchestration service
- Dispatch/matching service
- Pricing service (base + surge)
- Promotions service
- Payment service
- Earnings and payout service
- Ratings & reviews service
- Fraud/risk service
- Support/ticketing service
- Notification service

## Data platform responsibilities
- Event ingestion and durable streaming
- Historical storage in bronze/silver/gold layers
- Conformed analytics model (dimensions/facts)
- ML feature pipelines and offline training sets
- Embedding/vector pipelines for text intelligence
- Governance, lineage, quality, observability

## Separation principle
- Microservices optimize for transactional correctness and low-latency workflows.
- Data platform optimizes for cross-domain analytics, historical consistency, and AI readiness.

---

## 4) Ride lifecycle model (canonical)

### Primary lifecycle states
1. quote_requested
2. quote_generated
3. ride_requested
4. driver_assigned
5. driver_en_route
6. driver_arrived
7. trip_started
8. trip_in_progress
9. trip_completed
10. payment_authorized
11. payment_captured
12. payout_calculated
13. payout_disbursed
14. review_submitted
15. support_case_opened (optional)
16. refund_processed (optional)

### Cancellation branches
- rider_cancelled_pre_assign
- rider_cancelled_post_assign
- driver_cancelled
- system_cancelled

### Event-time principles
- Every event must include event_time and ingestion_time.
- Event IDs must be globally unique and immutable.
- Trip state transitions must be auditable.

---

## 5) Enterprise KPI catalog (minimum mandatory)

## Demand and supply
- Ride Requests: total requests per city/time
- Completed Trips: successfully fulfilled rides
- Completion Rate: completed_trips / requested_trips
- Driver Utilization: active_trip_time / online_time
- Rider Wait Time: request to pickup duration

## Revenue and profitability
- Gross Bookings: total fare before adjustments
- Net Revenue: platform_fee + service_fee - promotions - refunds
- Take Rate: net_revenue / gross_bookings
- Contribution Margin: net_revenue - variable_costs - incentives
- Driver Earnings: base + bonuses + tips - commissions

## Trust and quality
- Cancellation Rate by actor
- Fraud Loss Rate
- Support Ticket Rate per 1,000 trips
- Average Rating (rider and driver)
- SLA Breach Rate for key services

## Example formula governance
Every KPI definition must include:
- Business owner
- Technical owner
- SQL reference formula
- Grain (trip, rider-day, city-hour)
- Data freshness SLA
- Accepted null and edge-case behavior

---

## 6) Canonical entities and keys

## Business entities
- rider
- driver
- vehicle
- city
- trip
- payment
- promotion
- earnings
- review
- fraud_case
- support_ticket

## Key design
- Surrogate keys for warehouse dimensions
- Natural IDs preserved from source systems
- Stable business keys for cross-system joins
- Event IDs for idempotent processing

## Required IDs (examples)
- rider_id, driver_id, trip_id
- quote_id, request_id, payment_id
- support_ticket_id, fraud_case_id
- promotion_id, payout_id

---

## 7) Real-time vs batch responsibilities

## Real-time (seconds to minutes)
- Dispatch/matching optimization
- Surge signal generation
- Fraud anomaly scoring (near real-time)
- Live operations dashboards

## Batch (hourly to daily)
- Financial reconciliation
- Dimensional model refresh and aggregates
- Retraining datasets and model backfills
- City-level planning and executive reporting

## Hybrid pattern
- Lambda-like behavior implemented with unified lakehouse + incremental jobs
- Streaming writes base layers, batch hardens and reconciles

---

## 8) Data contracts and schema evolution policy

## Data contract fields (minimum)
- topic_name
- producer_service
- schema_version
- required_fields
- nullability
- PII_classification
- retention_policy
- quality_rules

## Evolution rules
- Backward-compatible changes: add optional fields
- Breaking changes: new schema version + migration window
- Contract enforcement at ingestion boundary
- Producer ownership with data platform review gate

## Governance workflow
1. Producer proposes schema change
2. Contract validation in CI
3. Data platform compatibility check
4. Controlled rollout with canary consumers
5. Lineage and documentation update

---

## 9) Observability and SLA design at domain stage

## SLA categories
- Data freshness SLA (e.g., ride events < 2 min to silver)
- Data quality SLA (e.g., trip_id completeness > 99.95%)
- Pipeline reliability SLA (e.g., monthly success > 99.5%)

## Logging taxonomy
- Structured pipeline logs (JSON)
- Error logs with error_code and stage
- Audit logs for reprocessing and overrides
- Data quality logs for rule outcomes

## Alerting examples
- Late-event spike by city
- Kafka consumer lag threshold breach
- Trip completion mismatch across domains
- Payment capture success drop

---

## 10) Partitioning and scale assumptions

## Scale baseline (local design target; enterprise-compatible)
- Up to millions of rides/day logical design
- City and event_date as primary partition axes
- High-cardinality IDs in clustering/sorting, not top-level partitions

## Recommended partition strategy
- Bronze: by ingest_date and source_topic
- Silver: by event_date and city_id
- Gold: by business grain (date, city, service_type)

## Streaming resilience concepts
- Exactly-once semantics where possible
- Checkpointing per query
- Idempotent writes keyed by event_id
- Dead-letter handling for poison events

---

## 11) Multi-region and multi-city operating model

## Expansion principles
- City is first-class dimension and partition key
- Regional isolation for regulatory constraints
- Global KPI harmonization with local overrides

## Data strategy
- Region-local ingestion and processing
- Cross-region replicated gold aggregates
- Region-aware lineage and retention policies

---

## 12) Cost optimization strategy from day zero

- Tiered storage (hot recent data, warm historical)
- Compaction and file-size optimization in lakehouse
- Incremental compute over full refreshes
- Reuse feature datasets across ML use cases
- Contract-driven schemas to reduce downstream breakage costs

---

## 13) Azure migration equivalent (Stage 0 conceptual mapping)

- Kafka -> Azure Event Hubs
- Spark Structured Streaming / Batch -> Azure Databricks
- Lakehouse (Parquet/Delta) -> ADLS Gen2 + Delta Lake
- PostgreSQL warehouse -> Azure SQL Database
- MongoDB -> Azure Cosmos DB (Mongo API)
- Vector DB (Weaviate/Chroma) -> Azure AI Search (vector)
- Ollama local runtime -> Azure OpenAI
- Airflow -> Azure Data Factory (or Fabric pipelines)
- Prometheus/Grafana -> Azure Monitor + Managed Grafana

## Migration principle
Keep business contracts, domain model, and KPI semantics cloud-agnostic; swap infrastructure adapters only.

---

## 14) Enterprise folder structure (target blueprint for later stages)

```text
Ride_hailing_data_ai_platform/
  docs/
    stages/
      stage-00-business-context-domain-modeling.md
  contracts/
    events/
    schemas/
  ingestion/
    kafka/
    simulators/
  processing/
    spark/
      bronze/
      silver/
      gold/
  lakehouse/
    bronze/
    silver/
    gold/
  warehouse/
    dbt/
  ml/
    features/
    models/
    training/
    inference/
  vector/
    embeddings/
    indexes/
  api/
    fastapi/
  observability/
    prometheus/
    grafana/
    logging/
  orchestration/
    airflow/
  docker/
    compose/
  scripts/
  tests/
```

---

## 15) Docker configuration direction (defined now, implemented in Stage 5)

Stage 0 decisions for container strategy:
- One docker-compose base file for core services
- Optional override files for heavy services (Spark, Airflow)
- Named volumes for durable local state
- Explicit internal network and service discovery aliases
- Health checks for startup dependency gating

Planned service groups:
- Messaging: Kafka (+ ZooKeeper/KRaft depending on chosen image)
- Compute: Spark master/worker (local cluster mode)
- Storage/OLTP: PostgreSQL, MongoDB
- Vector: Weaviate or Chroma service
- AI runtime: Ollama
- Monitoring: Prometheus + Grafana
- API: FastAPI container

---

## 16) Step-by-step implementation checklist for Stage 0

1. Approve business glossary and KPI definitions with stakeholders.
2. Finalize canonical ride lifecycle and state transitions.
3. Approve domain ownership matrix (microservice vs platform).
4. Define contract template and schema evolution workflow.
5. Approve scale assumptions (rides/day, cities, SLA targets).
6. Lock target folder blueprint and naming conventions.
7. Document Azure equivalence for executive roadmap alignment.
8. Freeze Stage 0 outputs as reference artifacts for Stage 1+.

---

## 17) Interview-ready talking points (concise)

- Stage 0 prevents downstream rework by aligning business semantics before engineering.
- Ride-hailing requires strict separation of operational truth and analytical truth.
- KPI governance is as critical as pipeline technology.
- City and time are the dominant axes for scale, quality, and cost control.
- Cloud migration success depends on portable contracts and model semantics.

---

## 18) Stage 0 exit criteria

Stage 0 is complete when:
- KPI catalog is approved
- Lifecycle and domain boundaries are signed off
- Data contract standard is defined
- Scale and SLA targets are documented
- Folder and platform blueprint are accepted
- Azure mapping is documented for future migration
