# Stage 7 - Spark Structured Streaming (Bronze / Silver / Gold)

## 1) Stage objective

Stage 7 implements continuous stream processing from Kafka into the lakehouse medallion architecture:
- Kafka -> Bronze raw persistence
- Bronze -> Silver canonicalization + data quality controls
- Silver -> Gold business aggregates

This stage operationalizes contract enforcement, event-time processing, and reliable incremental analytics.

---

## 2) Why this stage matters

In enterprise ride-hailing platforms, ingestion alone is insufficient. Value comes from transforming high-volume streams into trusted, queryable, and model-ready layers.

Stage 7 ensures:
- Replay-safe storage of raw source truth
- Contract-aware canonical model for downstream analytics/ML
- Real-time business metrics for operations and leadership

---

## 3) Data flow implemented

Source -> Kafka -> Spark Structured Streaming -> Bronze -> Silver -> Gold

### Bronze
- Stores immutable raw event payloads and Kafka metadata
- Preserves source replayability and traceability

### Silver
- Parses payloads to canonical event schema
- Applies required-field checks and deduplication
- Routes malformed records to quarantine

### Gold
- Produces city-hour aggregates (trips, financial measures, surge behavior)
- Supports operational dashboards and executive KPI slices

---

## 4) Metadata-driven processing design

Stage 7 uses config-driven mapping from:
- `processing/spark/config/topic_pipeline_config.json`

Config controls:
- Topic subscriptions
- Bronze entity mapping
- Kafka options
- Quality watermark policy

This avoids hardcoding and supports easy onboarding of additional domains.

---

## 5) Implemented Spark jobs

## 5.1 Bronze job
File:
- `processing/spark/bronze/bronze_kafka_to_bronze.py`

Behavior:
- Reads all configured Kafka topics as streaming sources
- Writes append-only raw parquet to Bronze by entity and ingest date
- Captures topic, partition, offset, timestamps, key/value, ingestion time

## 5.2 Silver job
File:
- `processing/spark/silver/silver_canonical_events.py`

Behavior:
- Reads Bronze streaming parquet
- Parses JSON payload to typed canonical columns
- Applies watermark on event time
- Deduplicates by `event_id`
- Splits valid vs invalid records
- Writes canonical events and quarantine outputs separately

## 5.3 Gold job
File:
- `processing/spark/gold/gold_city_hourly_metrics.py`

Behavior:
- Reads Silver canonical stream
- Computes city-hour metrics with event-time windows
- Aggregates trip completion/cancellation and core financial fields
- Writes partitioned Gold parquet for consumption

---

## 6) Checkpointing and fault tolerance

Each layer has independent checkpoint paths:
- Bronze: `/opt/spark/checkpoints/bronze/...`
- Silver: `/opt/spark/checkpoints/silver/...`
- Gold: `/opt/spark/checkpoints/gold/...`

Benefits:
- Safe restart after failure
- Offset/state continuity
- Reduced duplicate processing risk with dedup logic

---

## 7) Data quality and quarantine strategy

Silver applies minimum DQ gates:
- `event_id` required
- `event_time` required
- `city_id` required

Invalid records are written to:
- `lakehouse/silver/quarantine_events`

This establishes a governed pattern for contract drift handling.

---

## 8) Partitioning strategy

Implemented partitioning:
- Bronze: partition by `ingest_date`
- Silver: partition by `event_date`, `city_id`
- Gold: partition by `event_date`, `city_id`

This aligns with scalability goals for city/date-heavy access patterns.

---

## 9) Late data and dedup handling

- Event-time watermark configured from metadata policy
- Silver dropDuplicates by `event_id`
- Gold windowed aggregations with watermark awareness

This handles typical ride-hailing streaming realities (late and duplicate events).

---

## 10) Observability and SLA hooks

Stage 7 provides clear hook points for monitoring:
- Query names per streaming job
- Quarantine volume as DQ signal
- Layer-level checkpoint health and lag indicators

Recommended SLO alignment:
- Silver freshness for P0 domains within minutes
- Quarantine breach thresholds with alerts

---

## 11) Enterprise implementation pattern (Uber-like)

Common enterprise pattern reflected here:
- Immutable raw stream vault (Bronze)
- Contracted and deduplicated semantic stream (Silver)
- KPI-ready aggregates (Gold)
- Quarantine and replay support for operational reliability

---

## 12) Azure migration equivalent

Open-source local -> Azure mapping:
- Spark Structured Streaming -> Azure Databricks Structured Streaming
- Lakehouse parquet/delta -> ADLS + Delta Lake
- Kafka -> Event Hubs
- Monitoring -> Azure Monitor and Managed Grafana

Migration principle:
Keep event contracts, transformations, and layer semantics unchanged while swapping managed compute/storage.

---

## 13) Runbook and execution

Runbook file:
- `processing/spark/README.md`

Core submit commands included for:
- Bronze streaming job
- Silver streaming job
- Gold streaming job

---

## 14) Stage 7 implementation assets

- `processing/spark/config/topic_pipeline_config.json`
- `processing/spark/common/spark_session.py`
- `processing/spark/common/pipeline_config.py`
- `processing/spark/bronze/bronze_kafka_to_bronze.py`
- `processing/spark/silver/silver_canonical_events.py`
- `processing/spark/gold/gold_city_hourly_metrics.py`
- `processing/spark/README.md`

---

## 15) Stage 7 exit criteria

Stage 7 is complete when:
- Bronze raw streams persist all configured topics
- Silver canonical output and quarantine are both active
- Gold city-hour aggregate stream is active
- Checkpointing and restart behavior are validated
- Stage 8 (dbt warehouse modeling) can consume stable Gold outputs
