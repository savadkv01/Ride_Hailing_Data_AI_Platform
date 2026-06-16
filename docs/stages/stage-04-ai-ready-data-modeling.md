# Stage 4 - AI-Ready Data Modeling (Operational + Dimensional + Vector)

## 1) Stage objective

Stage 4 defines the canonical enterprise data model that simultaneously supports:
- Operational analytics and near-real-time decisioning
- Finance-grade dimensional reporting
- ML feature engineering and model training
- Vector search and RAG-driven intelligence

This stage ensures all data products derive from one aligned semantic foundation.

---

## 2) Why AI-ready modeling is different from classic BI-only modeling

Traditional BI models optimize mostly for historical reporting. Ride-hailing platforms need a broader model design:
- Streaming + batch coexistence
- State transitions and event timelines
- Point-in-time feature correctness
- Unstructured text + embeddings
- Fraud/support investigation traceability

Therefore, the model must include:
1. Operational event model (high granularity)
2. Dimensional star schema (governed business KPIs)
3. Feature-friendly curated entities (ML)
4. Vector document/chunk schema (RAG)

---

## 3) Canonical modeling layers

## 3.1 Operational canonical layer (Silver)
Purpose:
- Preserve event-grain truth with validated contracts
- Standardize open + synthetic source fields

Entity groups:
- trip_events
- driver_location_events
- rider_app_events
- payment_events
- promotion_events
- refund_events
- earnings_events
- review_events
- fraud_signal_events
- support_ticket_events

## 3.2 Analytical dimensional layer (Gold + PostgreSQL dbt)
Purpose:
- Stable KPI semantics and high-performance slicing

Dimensions:
- dim_rider
- dim_driver
- dim_vehicle
- dim_city
- dim_time
- dim_promotion
- dim_payment_method

Facts:
- fact_trip
- fact_driver_earnings
- fact_payment
- fact_review
- fact_fraud
- fact_operational_event

## 3.3 AI serving layer
Purpose:
- Reusable features and vectorized corpora

Stores:
- Feature datasets/tables (offline + near-online)
- Vector indexes/collections for semantic retrieval

---

## 4) Operational data model (event-driven)

## 4.1 Canonical event envelope
All event-domain tables should include:
- event_id (immutable unique)
- event_type
- event_time
- ingestion_time
- source_system
- source_record_id
- schema_version
- city_id
- correlation_id (trip/request/session)

## 4.2 Trip lifecycle model
`trip_events` captures each state transition:
- quote_requested
- quote_generated
- ride_requested
- driver_assigned
- driver_arrived
- trip_started
- trip_completed
- trip_cancelled

Essential keys:
- trip_id, rider_id, driver_id, city_id
- vehicle_id, request_id, quote_id

## 4.3 Driver location model
`driver_location_events` grain:
- one GPS ping per driver per timestamp

Fields:
- driver_id, event_time, lat, lng, speed_kph, bearing, online_status, city_id

## 4.4 Rider app behavior model
`rider_app_events` grain:
- one app interaction event

Fields:
- session_id, rider_id, event_name, screen_name, event_time, city_id, app_version

## 4.5 Payment and settlement model
`payment_events` includes lifecycle states:
- authorization_requested
- authorization_succeeded
- capture_succeeded
- capture_failed
- chargeback_opened
- refund_processed

Fields:
- payment_id, trip_id, rider_id, method_code, amount, currency, status, gateway_ref

## 4.6 Promotions and incentives model
- `promotion_events`: campaign exposure, eligibility, redemption
- `incentive_events`: driver incentive qualification and payout adjustments

## 4.7 Fraud and support operational model
- `fraud_signal_events`: feature snapshot, rule hits, model score, decision action
- `support_ticket_events`: ticket open/update/resolve lifecycle + category/severity

---

## 5) Dimensional model design (warehouse truth)

## 5.1 Conformed dimensions
All facts must join to shared conformed dimensions for consistency.

### `dim_rider`
- rider_key (surrogate)
- rider_id (business key)
- signup_date_key
- rider_segment
- home_city_key
- lifecycle_status
- is_current, effective_from, effective_to (SCD2 where needed)

### `dim_driver`
- driver_key, driver_id
- onboarding_date_key
- vehicle_key
- driver_tier
- city_key
- lifecycle_status
- rating_band
- SCD attributes

### `dim_vehicle`
- vehicle_key, vehicle_id
- type, make, model, year
- plate_region
- capacity

### `dim_city`
- city_key, city_id
- city_name
- country_code
- timezone
- region_cluster
- regulatory_tier

### `dim_time`
- time_key/date_key (depending on grain)
- full timestamp/date attributes
- hour, weekday, month, quarter, holiday flags

### `dim_promotion`
- promotion_key, promotion_id
- campaign_type
- discount_type
- cap_amount
- valid_from, valid_to

### `dim_payment_method`
- payment_method_key, method_code
- method_type
- provider
- risk_profile

## 5.2 Fact model definitions

### `fact_trip` (grain: one row per trip outcome)
Measures:
- requested_count
- completed_flag
- cancelled_flag
- trip_distance_km
- trip_duration_sec
- quoted_fare
- final_fare
- surge_multiplier
- promotion_amount
- platform_fee
- driver_payout

Foreign keys:
- rider_key, driver_key, vehicle_key, city_key
- request_time_key, pickup_time_key, dropoff_time_key
- promotion_key, payment_method_key

### `fact_driver_earnings` (grain: one earning transaction)
Measures:
- base_earning
- surge_bonus
- incentive_bonus
- tip_amount
- adjustment_amount
- net_driver_earning

### `fact_payment` (grain: one payment transaction event)
Measures:
- authorized_amount
- captured_amount
- refunded_amount
- chargeback_amount
- fee_amount

### `fact_review` (grain: one submitted review)
Measures:
- rating_value
- sentiment_score
- response_time_sec

### `fact_fraud` (grain: one fraud assessment/action)
Measures:
- fraud_score
- risk_band
- blocked_flag
- reviewed_flag
- confirmed_fraud_flag
- estimated_loss_amount

### `fact_operational_event` (grain: one operational event)
Measures:
- event_count
- latency_ms
- processing_delay_sec

---

## 6) Model alignment with open + synthetic sources

Stage 3 established canonical alignment specs. Stage 4 enforces model-level consistency:
- Open datasets first map to canonical operational events
- Synthetic streams directly emit canonical contracts
- Gold facts only consume canonicalized Silver entities

Alignment artifacts:
- `config/source_catalog/canonical_alignment.yaml`
- `docs/standards/open-synthetic-alignment-standard.md`

---

## 7) Feature-oriented data model

## 7.1 Feature table patterns
- `feature_trip_demand_city_15m`
- `feature_supply_driver_zone_5m`
- `feature_rider_behavior_30d`
- `feature_driver_churn_weekly`
- `feature_fraud_risk_realtime`

## 7.2 Feature metadata fields
Every feature table should carry:
- feature_name
- feature_timestamp
- entity_id (rider/driver/trip/city)
- feature_value(s)
- feature_version
- source_snapshot_id
- generation_run_id

## 7.3 Point-in-time correctness
Features used for training/inference must be computed only from data available at prediction time.

---

## 8) Vector data model (semantic layer)

## 8.1 Collections/indexes
- reviews_index
- support_tickets_index
- trip_notes_index
- policy_docs_index
- faq_docs_index
- fraud_cases_index

## 8.2 Canonical vector record schema
- vector_id
- doc_id
- source_type
- city_id
- entity_id (trip_id/ticket_id/case_id as applicable)
- text_chunk
- embedding_vector
- embedding_model
- chunk_index
- language_code
- created_at
- pii_level
- tags (JSON)

## 8.3 Chunking strategy
- Policy/FAQ: semantic chunking by section
- Tickets/cases: conversational turns or incident segments
- Reviews: one review per chunk with optional normalization

## 8.4 RAG retrieval metadata filters
- city_id
- date range
- source_type
- risk category
- language

---

## 9) Data contracts and schema evolution at model level

## 9.1 Contract requirements
For each modeled table/entity:
- owner_team
- business definition
- grain
- primary/business keys
- required fields
- nullability rules
- SLA target
- downstream dependencies

## 9.2 Evolution policy
- Additive non-breaking columns allowed with version update
- Breaking grain/key changes require new model version and migration path
- dbt documentation/tests updated in same release

---

## 10) Data quality model rules

## 10.1 Key rules
- PK uniqueness (`event_id`, fact transaction IDs)
- Mandatory FK validity to conformed dimensions
- Non-negative fare/distance/duration/amounts where applicable
- Reconciliation checks:
  - trip financial components sum correctly
  - payment/refund links are traceable

## 10.2 Semantic rules
- Trip lifecycle sequence consistency
- Fraud decision states follow allowed transitions
- Support ticket closure requires resolution metadata

## 10.3 DQ outputs
- Pass/fail metrics by table and city
- Quarantine records for violations
- Alert thresholds tied to SLA severity

---

## 11) Lineage and audit model

Lineage fields recommended in all layers:
- source_system
- source_record_id
- ingestion_run_id
- transformation_run_id
- contract_version
- created_at
- updated_at

Audit tables:
- pipeline_run_audit
- dq_rule_audit
- model_version_audit
- backfill_audit

---

## 12) Performance and partitioning design

## 12.1 Lakehouse partitioning
- Silver operational tables: `event_date`, `city_id`
- Gold facts: `date_key` (or `event_date`) + `city_id`

## 12.2 Clustering/index strategy
- Cluster/order by high-selectivity keys (`trip_id`, `driver_id`) where relevant
- PostgreSQL indexes on fact FK columns + date/city filters

## 12.3 Late data handling
- Event-time watermarks in streaming
- Merge-upsert logic for mutable business outcomes
- Reconciliation jobs for financial correctness

---

## 13) Multi-city and multi-region model considerations

- `city_id` is mandatory across operational, dimensional, and vector schemas
- Region-specific regulatory attributes captured in `dim_city`
- Policy documents and support corpora tagged by geography and language
- KPI definitions remain global, with local parameter overlays

---

## 14) Security and governance in model design

- PII-classification columns in metadata catalog
- Masked/pseudonymous IDs in non-production datasets
- Row/column-level access policy by persona (analyst, support, fraud, finance)
- Retention policy by domain (trip, payment, support, vector text)

---

## 15) How Uber-like companies model this in practice

Enterprise pattern:
- Event-driven operational model as system-of-record for behavior
- Curated dimensional layer for controlled KPI truth
- Specialized feature and vector models for AI use cases
- Strong contract ownership and schema governance across domains

The core advantage is one semantic backbone feeding many products without redefinition.

---

## 16) Azure migration equivalent for model layer

- Operational canonical tables on lakehouse: Delta on ADLS + Databricks
- Dimensional models: dbt to Azure SQL/Synapse
- Feature pipelines: Databricks + Azure ML-compatible stores
- Vector indexes: Azure AI Search
- LLM runtime: Azure OpenAI
- Governance and lineage: Azure-native catalog/monitoring equivalents

Migration principle:
Preserve model semantics, keys, grain, and KPI logic; swap compute/storage adapters.

---

## 17) Folder structure impact for implementation stages

Recommended additions/usage:
- `contracts/models/` for table-level contracts
- `warehouse/dbt/models/dimensions/`
- `warehouse/dbt/models/facts/`
- `ml/features/definitions/`
- `vector/schemas/`
- `config/model_catalog/`

---

## 18) Step-by-step implementation plan (Stage 4 scope)

1. Finalize canonical operational entity schemas and event envelopes.
2. Lock conformed dimensions and fact grains.
3. Define feature table schemas with point-in-time guarantees.
4. Define vector schema and chunking/metadata strategy.
5. Define model contracts and evolution rules.
6. Define DQ, lineage, and audit schemas.
7. Approve partitioning/index strategy per layer.
8. Freeze Azure-equivalent model mapping.

---

## 19) Interview-ready talking points

- We model once for operations, analytics, and AI by separating event-grain truth from KPI-grain facts.
- Conformed dimensions prevent metric drift across domains.
- AI readiness requires both feature schemas and vector schemas, not just star schema tables.
- Contract-first evolution and DQ/audit fields are built into the model design, not added later.

---

## 20) Stage 4 exit criteria

Stage 4 is complete when:
- Operational, dimensional, and vector schemas are defined.
- Fact grains and dimension conformance are approved.
- Feature and vector model standards are documented.
- Contract, lineage, and DQ expectations are formalized.
- Partitioning and scaling design is agreed.
- Azure-equivalent model mapping is documented.
