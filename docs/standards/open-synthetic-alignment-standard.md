# Open + Synthetic Source Alignment Standard

## Objective
Ensure NYC open trips, Chicago open trips, and synthetic ride-hailing events are aligned into a single canonical platform model so all downstream layers (Bronze/Silver/Gold, warehouse, ML, vector, API) produce consistent results.

## Alignment Status
- Conceptual alignment: Complete
- Canonical mapping config: Complete
- Runtime enforcement: Planned for ingestion/processing stages

## Canonical Contract
Canonical mapping is defined in:
- config/source_catalog/canonical_alignment.yaml

This file defines:
- Canonical required fields
- Per-source mapping transforms
- Alignment validation rules
- Domain completeness requirements

## Alignment Decisions
1. Use one canonical trip-event contract for open + synthetic trip records.
2. Normalize distance to kilometers and duration to seconds.
3. Normalize monetary logic into `fare_total`, `platform_fee`, `driver_payout`, `promotion_amount`.
4. Create pseudonymous rider/driver IDs for open datasets.
5. Keep source lineage fields (`source_system`, `source_record_id`, `schema_version`).
6. Treat missing open-data fields as enriched/derived fields during Silver transformation.

## What this means for your question
Yes—NYC/Chicago and synthetic data are now aligned at the platform-contract level via canonical mapping rules.

Important caveat:
- The alignment is currently defined as standard + metadata config.
- Physical runtime enforcement will be implemented in Stage 6/7 ingestion and streaming jobs.

## Enforcement Plan
- Stage 6: Validate source payloads against canonical mapping and contract version.
- Stage 7: Enforce alignment rules in Silver transformations and data quality checks.
- Stage 8+: Ensure warehouse/dbt models consume only canonicalized Silver/Gold datasets.

## Enterprise Benefits
- One business truth across open and synthetic feeds
- Lower schema drift risk
- Reusable transformations across cities
- Consistent ML feature and model behavior
- Reliable governance and lineage

## Azure Equivalence
The same alignment standard migrates directly:
- Event ingestion: Kafka -> Event Hubs
- Validation/transforms: Spark -> Databricks
- Contract catalog: local metadata -> Azure SQL/Databricks tables
- Data quality observability: Prometheus/Grafana -> Azure Monitor
