# Stage 1 - Enterprise Ride Data Architecture

## 1) Stage objective

Stage 1 converts business/domain understanding into a production-grade architecture blueprint for a ride-hailing data and AI platform. This architecture is designed for:
- Local execution on Windows with Docker + VS Code
- Open-source-first implementation
- Enterprise scalability to millions of rides/day
- Clear separation between operational services and analytical/AI platform

This stage is architecture-only (design and decisions). Implementation starts in later stages.

---

## 2) Architecture principles (enterprise)

1. Domain-first architecture
   - Services and data models follow ride-hailing business capabilities.
2. Event-driven core
   - Critical operational state transitions are emitted as immutable events.
3. Lakehouse-centric analytics backbone
   - Unified storage supports streaming, batch, ML features, and BI.
4. Contract-first ingestion
   - Producers publish against versioned schemas and data contracts.
5. Metadata-driven pipelines
   - Topic-to-table mappings, quality rules, and transformations are config-driven.
6. Polyglot persistence
   - PostgreSQL (warehouse), MongoDB (operational/semi-structured), vector DB (semantic retrieval).
7. AI-native by design
   - Features, embeddings, and RAG are first-class platform capabilities.
8. Observability-by-default
   - Structured logging, metrics, lineage, DQ checks, and SLA alerting.

---

## 3) Reference architecture (logical layers)

## A) Operational application layer (OLTP / microservices)
Microservices generate transactional events and command data:
- Rider, Driver, Vehicle profile services
- Trip orchestration and dispatch services
- Pricing and surge service
- Promotions and incentives service
- Payment and payout service
- Ratings/reviews service
- Fraud/risk and support service

Primary purpose:
- Serve app flows at low latency
- Persist transactional consistency
- Emit domain events for downstream analytics/AI

## B) Streaming ingestion layer
- Apache Kafka as central event backbone
- Topics partitioned by city/time/domain key
- Consumer groups for replay and independent scaling
- Optional Schema Registry pattern (open-source equivalent via contract tables/files)

Primary purpose:
- Decouple producers/consumers
- Enable near real-time pipelines and reprocessing

## C) Stream processing + batch layer
- Spark Structured Streaming for real-time transformations
- Spark batch jobs for reconciliation and backfills

Primary purpose:
- Convert raw events into reliable curated datasets
- Handle late events, deduplication, enrichment, and quality checks

## D) Lakehouse storage layer (Bronze/Silver/Gold)
- Open-source Delta Lake or Parquet-based lakehouse
- Bronze: raw immutable landing
- Silver: cleaned, conformed, deduplicated
- Gold: business-ready marts and aggregates

Primary purpose:
- Single source for analytics, ML feature generation, and downstream serving

## E) Warehouse + semantic modeling layer
- PostgreSQL as dimensional warehouse
- dbt for ELT modeling, tests, docs, and lineage

Primary purpose:
- Star schema for BI/reporting and governed KPI computation

## F) Operational + semi-structured data layer
- MongoDB for operational artifacts (support context, app session traces, flexible JSON docs)

Primary purpose:
- Fast retrieval and flexible schema where strict normalization is not practical

## G) Vector intelligence layer
- Weaviate or Chroma for vector embeddings
- Stores reviews, support tickets, policy docs, trip notes, fraud narratives

Primary purpose:
- Semantic search and RAG retrieval

## H) AI/ML layer
- Feature pipelines from gold/silver
- Models: demand forecast, dynamic pricing, churn, fraud
- Local LLM runtime via Ollama

Primary purpose:
- Predictive and generative intelligence integrated with platform data

## I) API serving layer
- FastAPI for model inference, analytics access, and RAG endpoints

Primary purpose:
- Productize data and AI capabilities for internal/external consumers

## J) Observability and governance layer
- Prometheus + Grafana for metrics dashboards
- Structured logs and audit logs
- Data quality checks and SLA alerting

Primary purpose:
- Reliable operations, trust, and compliance at scale

---

## 4) End-to-end data flow (canonical)

Source Systems
-> Kafka Topics
-> Spark Structured Streaming
-> Bronze (raw)
-> Silver (validated/conformed)
-> Gold (business-ready)

Gold is consumed by:
1. PostgreSQL warehouse (via dbt dimensional models)
2. ML feature layer and model training/scoring
3. Embedding pipeline -> vector database

API layer consumes:
- Warehouse aggregates
- ML model endpoints/features
- Vector retrieval + Ollama generation

---

## 5) Required event domains and topic groups

The platform must capture at least:
1. Real-time ride events
2. Driver location streaming
3. Rider app events
4. Trip lifecycle tracking
5. Payment processing
6. Surge pricing logic
7. Discounts and promotions
8. Refunds
9. Ratings and reviews
10. Driver earnings
11. Incentives
12. Fraud signals
13. Customer support logs
14. Geo-location data
15. City-level aggregation inputs
16. Revenue/margin/platform fee data

## Example topic naming convention
`rh.<domain>.<entity>.<event>.v<version>`

Examples:
- `rh.trip.lifecycle.events.v1`
- `rh.driver.location.pings.v1`
- `rh.payment.transactions.v1`
- `rh.support.tickets.v1`
- `rh.fraud.signals.v1`

---

## 6) Metadata-driven framework design

## A) Config-driven ingestion catalog
Create metadata tables/files to avoid hard-coded pipelines:
- ingestion_config
- topic_schema_registry
- topic_to_bronze_mapping
- quality_rule_config
- silver_transform_config
- gold_model_config

## B) Suggested config fields
- source_topic
- target_layer
- target_table
- key_columns
- watermark_column
- dedup_logic
- partition_columns
- expected_schema_version
- quality_rule_set
- sla_minutes
- owner_team

## C) Runtime behavior
- Spark job reads config
- Dynamically binds topic -> parsing -> destination table
- Applies configurable data quality and error routing
- Emits pipeline metrics and audit records

Enterprise benefit:
- Faster onboarding of new domains/cities
- Lower code duplication
- Controlled schema evolution

---

## 7) Data model targets (high level at architecture stage)

## Dimensions
- dim_rider
- dim_driver
- dim_vehicle
- dim_city
- dim_time
- dim_promotion
- dim_payment_method

## Facts
- fact_trip
- fact_driver_earnings
- fact_payment
- fact_review
- fact_fraud
- fact_operational_event

## Additional serving stores
- Mongo collections for semi-structured operational support context
- Vector collections/indexes for semantic corpora

---

## 8) Microservices vs data platform (responsibility split)

## Microservices own
- Transaction correctness
- Real-time command workflows
- Source event generation
- User-facing SLAs

## Data platform owns
- Historical consolidation
- Cross-domain joins and KPI truth
- ML features and model lifecycle data paths
- Data quality, lineage, and governance

## Shared contract
- Versioned event schemas
- Semantic definitions (field meanings)
- Backward compatibility policy
- Incident ownership matrix

---

## 9) Real-time vs batch architecture details

## Real-time path
- Ingest from Kafka continuously
- Process with event-time windows and watermarking
- Deliver operational dashboards and near-real-time AI signals

## Batch path
- Periodic reprocessing for correctness and late-arriving events
- Financial reconciliation and ledger alignment
- Historical backfill for model retraining

## Convergence strategy
- Silver/Gold as convergence points where real-time and batch outputs are reconciled

---

## 10) Data contracts and schema evolution architecture

## Contract repository pattern
- Contracts stored as versioned JSON/YAML + approval workflow
- Producers declare required/optional fields and semantics
- CI validation checks backward compatibility

## Evolution patterns
- Additive optional fields: same major version
- Breaking field semantic/type changes: new versioned topic or schema version bump
- Sunset policy with dual-write transition window

## Runtime enforcement
- Contract validation at ingestion
- Invalid payload -> dead-letter + alert
- Contract drift dashboards in observability layer

---

## 11) Lineage, quality, and governance architecture

## Lineage
- Track source topic -> bronze -> silver -> gold -> dbt model -> API/ML consumer

## Data quality gates
- Schema validity
- Mandatory key completeness
- Referential checks against dimensions
- Duplication thresholds
- Business-rule checks (fare >= 0, trip_distance >= 0)

## Governance controls
- PII classification tags
- Access tiers by role
- Retention and deletion policy
- Audit trails for replay/reprocessing

---

## 12) Observability architecture

## Logging
- JSON structured logs for all services/jobs
- Correlation IDs: trip_id, rider_id, driver_id, request_id
- Error classification and retry metadata

## Metrics
- Kafka lag, throughput, consumer health
- Spark micro-batch duration, input rows/sec, state store growth
- Data freshness lag by domain/table
- DQ pass/fail counts
- API latency/error rates

## Dashboards and alerts
- Grafana dashboards by domain and pipeline stage
- Alert routing by severity and ownership team

---

## 13) Scalability architecture (millions of rides/day)

## Partitioning strategy
- Kafka: partition by city_id and high-volume key strategy
- Lakehouse: partition by event_date, city_id, domain
- Warehouse: indexes and partitioned fact tables by date/city

## Streaming resilience
- Structured Streaming checkpointing per query
- Backpressure handling through trigger tuning and autoscale policy
- Idempotent upserts/merges for exactly-once-like behavior
- Dead-letter and replay channels

## Horizontal scaling
- Add Kafka partitions and consumers
- Scale Spark executors/workers
- Separate workloads by domain priority

## Cost controls
- Incremental processing instead of full scans
- Data compaction/vacuum lifecycle
- Right-sized retention windows per layer

---

## 14) Multi-region and disaster resilience blueprint

## Multi-region pattern
- Region-local ingestion and processing for sovereignty/latency
- Federated gold summaries for global analytics
- Region-tagged datasets and lineage

## Disaster recovery
- Metadata and contract backup
- Cross-region replication for critical gold datasets
- Recovery runbooks for Kafka offsets/checkpoints

---

## 15) Security architecture baseline

- Secrets externalized from code and compose files
- Role-based access (platform, analyst, ML, support)
- Encryption in transit and at rest
- PII masking/tokenization for non-production use
- Least-privilege service accounts for pipelines

---

## 16) Local Docker topology (Stage 1 design, Stage 5 implementation)

Core containers:
- Kafka
- Spark (master + worker)
- PostgreSQL
- MongoDB
- Weaviate/Chroma
- Ollama
- FastAPI
- Prometheus
- Grafana

Network zones (logical):
- ingest_net
- processing_net
- serving_net
- monitoring_net

Persistence:
- Named volumes for stateful services
- Bind mounts for configs, jobs, dbt models

---

## 17) Azure equivalent mapping (architecture-level)

- Kafka -> Event Hubs
- Spark -> Azure Databricks
- Lakehouse -> ADLS Gen2 + Delta
- PostgreSQL -> Azure SQL
- MongoDB -> Cosmos DB (Mongo API)
- Weaviate/Chroma -> Azure AI Search (vector indexes)
- Ollama -> Azure OpenAI
- Airflow -> Azure Data Factory
- Prometheus/Grafana -> Azure Monitor + Managed Grafana

## Migration strategy principle
Preserve domain contracts, metric definitions, and pipeline semantics; replace infrastructure layer per environment.

---

## 18) SLA architecture design

Define SLA classes:
- P0 (mission critical): trip lifecycle, payment, fraud alerts
- P1 (high): driver/rider behavioral streams, support logs
- P2 (standard): daily reporting enrichments

Sample targets:
- Streaming silver freshness <= 2 minutes for P0/P1 domains
- Gold availability >= 99.5% monthly
- Critical pipeline recovery objective <= 30 minutes

---

## 19) Interview-ready architecture narrative

"We designed an event-driven, metadata-driven ride-hailing platform with clear transactional vs analytical boundaries. Kafka and Spark Structured Streaming feed a bronze/silver/gold lakehouse, then dbt models in PostgreSQL for dimensional analytics. In parallel, the same curated data powers ML features and vector/RAG capabilities through Weaviate/Chroma and Ollama. The architecture enforces contracts, schema evolution, observability, and SLA governance, and remains cloud-portable through one-to-one Azure service mappings."

---

## 20) Stage 1 implementation checklist

1. Approve logical architecture layers and responsibilities.
2. Approve canonical data flow and topic grouping.
3. Approve metadata config model and contract governance.
4. Approve dimensional model scope and serving stores.
5. Approve observability, SLA classes, and ownership model.
6. Approve scale assumptions and partitioning strategies.
7. Freeze Azure mapping for executive migration narrative.

---

## 21) Stage 1 exit criteria

Stage 1 is complete when:
- End-to-end architecture is documented and signed off.
- Domain boundaries are explicit and owned.
- Data flow from source to AI/vector serving is agreed.
- Metadata-driven pattern is defined.
- Scalability, SLA, and observability patterns are documented.
- Azure equivalence is documented without changing business semantics.
