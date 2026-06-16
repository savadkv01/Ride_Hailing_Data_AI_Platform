# Stage 5 - Full Docker Infrastructure Setup

## 1) Stage objective

Stage 5 defines the production-style local infrastructure blueprint for the full ride-hailing data and AI platform on Windows using Docker and VS Code.

This stage provides:
- Enterprise Docker topology
- Compose layering strategy
- Service-level config standards
- Data persistence and networking conventions
- Logging/observability bootstrap
- Security baseline
- Scalability patterns
- Azure migration equivalence

This stage is architecture + implementation guide. Runtime implementation starts from Stage 6 onward.

---

## 2) Why this stage matters

For enterprise data platforms, infrastructure consistency determines reliability. Without a strict local infrastructure standard:
- Teams run incompatible stacks
- Debugging is inconsistent
- Data persistence breaks between runs
- Service dependencies fail at startup
- Observability is fragmented

Stage 5 ensures every developer and CI-like local run starts from one deterministic environment.

---

## 3) Core open-source stack (local)

Required platform services:
- Kafka (event streaming backbone)
- Spark (stream + batch compute)
- PostgreSQL (dimensional warehouse)
- MongoDB (operational/semi-structured)
- Weaviate or Chroma (vector database)
- Ollama (local LLM runtime)
- FastAPI (platform API serving)
- Prometheus + Grafana (monitoring)

Optional:
- Airflow (orchestration)

---

## 4) Enterprise Docker architecture (logical)

## 4.1 Service groups
1. Ingestion group
   - Kafka broker + controller mode support
2. Processing group
   - Spark master and workers
3. Persistence group
   - PostgreSQL, MongoDB, Lakehouse volumes
4. AI and vector group
   - Ollama, Weaviate/Chroma
5. Serving group
   - FastAPI
6. Monitoring group
   - Prometheus, Grafana
7. Optional orchestration group
   - Airflow webserver/scheduler/worker + metadata DB

## 4.2 Network segmentation
Logical networks in compose:
- platform_core_net
- serving_net
- monitoring_net

Pattern:
- Internal communication stays container-to-container
- Only required ports are published to host

---

## 5) Compose file strategy (enterprise local)

Use layered compose design:

1. Base compose
- docker/compose/docker-compose.base.yml
- Core services and shared networks/volumes

2. Processing override
- docker/compose/docker-compose.spark.yml
- Spark master/worker tuning and mount paths

3. Optional orchestration override
- docker/compose/docker-compose.airflow.yml

4. Observability override
- docker/compose/docker-compose.monitoring.yml

5. Local profile files
- docker/compose/.env.local
- docker/compose/.env.enterprise-sim

Benefits:
- Faster startup for partial stacks
- Clear environment-specific tuning
- Lower developer resource usage when full stack is not required

---

## 6) Recommended enterprise folder structure (infrastructure)

```text
Ride_hailing_data_ai_platform/
  docker/
    compose/
      docker-compose.base.yml
      docker-compose.spark.yml
      docker-compose.monitoring.yml
      docker-compose.airflow.yml
      .env.local
      .env.enterprise-sim
    kafka/
      server.properties
      topics-bootstrap.sh
    spark/
      spark-defaults.conf
      log4j2.properties
    postgres/
      init/
      conf/
    mongodb/
      init/
    weaviate/
      weaviate.env
    ollama/
      models.txt
    prometheus/
      prometheus.yml
      alerts.yml
    grafana/
      provisioning/
      dashboards/
  lakehouse/
    bronze/
    silver/
    gold/
  logs/
    pipeline/
    app/
    audit/
```

---

## 7) Windows-specific implementation considerations

1. Docker Desktop
- Use Linux containers mode
- Enable WSL2 integration

2. Path handling
- Use forward-slash style mount paths in compose where possible
- Avoid deep nested bind mounts with unstable permissions

3. Resource sizing
- Configure Docker Desktop CPU/RAM to support Spark + Kafka + DBs
- Recommended profile for enterprise simulation: higher memory class

4. Line endings
- Use LF for shell scripts mounted into Linux containers

5. Volume strategy
- Use named volumes for stateful services to reduce Windows filesystem overhead

---

## 8) Service-level infrastructure standards

## 8.1 Kafka
- Define retention per topic class
- Configure partition baseline for high-volume domains
- Set listener/adverstised listener correctly for inter-container + host access
- Add bootstrap topic initialization script

## 8.2 Spark
- One master + N workers profile-driven
- Externalized configs for shuffle, memory, and checkpoint behavior
- Mount jobs/config directories as read-only where possible

## 8.3 PostgreSQL
- Dedicated database for warehouse and metadata
- Init scripts for schemas/roles
- WAL and checkpoint settings suitable for local throughput

## 8.4 MongoDB
- Auth-enabled local setup
- Initialization scripts for base collections/indexes

## 8.5 Vector database (Weaviate or Chroma)
- Persistent index storage volume
- Collection/class bootstrap config
- API exposure only on required port

## 8.6 Ollama
- Controlled local model list and version policy
- Volume mount for model cache persistence

## 8.7 FastAPI
- Internal DNS-based endpoints to downstream services
- Health endpoint for compose readiness checks

## 8.8 Prometheus/Grafana
- Prometheus scrape targets for each service
- Grafana dashboards pre-provisioned in repo
- Alert rules for lag, failures, freshness, and resource saturation

---

## 9) Lakehouse storage and persistence design

## 9.1 Local persistence model
- Bronze/Silver/Gold as mounted storage paths or named volumes
- Structured subpaths by domain/date/city

## 9.2 Stateful service volumes
Required durable volumes:
- kafka_data
- postgres_data
- mongodb_data
- vector_data
- ollama_data
- grafana_data
- spark_checkpoints
- lakehouse_data

## 9.3 Data lifecycle controls
- Retention cleanup scripts by layer
- Compaction job schedule placeholders
- Snapshot/backup scripts for critical metadata stores

---

## 10) Metadata-driven infra controls

Infrastructure should read from configuration rather than hardcoding values:
- topic definitions
- service endpoints
- database/schema names
- checkpoint paths
- DQ thresholds
- SLA thresholds

Config files:
- config/source_catalog/
- config/model_catalog/
- config/sla/
- config/monitoring/

This keeps infra and pipeline behavior synchronized across stages.

---

## 11) Observability and logging setup (mandatory)

## 11.1 Structured logging
- JSON logs for pipeline/app services
- Mandatory correlation fields:
  - trip_id
  - rider_id
  - driver_id
  - city_id
  - pipeline_run_id

## 11.2 Log classes
- Pipeline logs
- Error logs
- Audit logs
- Data quality logs

## 11.3 Metrics and dashboards
- Kafka lag by topic/consumer group
- Spark micro-batch latency and input rate
- Warehouse load latency
- API latency and error rate
- Vector retrieval latency
- LLM response timing

## 11.4 Alerts
- P0: trip/payment/fraud stream disruption
- P1: delayed gold refresh
- P2: dashboard model drift signals

---

## 12) Security baseline for local enterprise setup

- Use environment files for secrets (never hardcode in compose)
- Create separate service credentials
- Restrict host-exposed ports to minimum
- Enable role-based DB users
- Keep PII masked in non-production sample data
- Use read-only mounts for immutable configs where possible

---

## 13) SLA and reliability controls at infra layer

Define infra SLOs:
- Container health uptime target
- Stream pipeline recoverability target
- Data freshness targets by domain tier

Reliability patterns:
- Healthchecks for dependent startup ordering
- Restart policies with bounded retries
- Checkpointed streaming recovery
- Dead-letter topics/collections for malformed events

---

## 14) Scalability design in Docker context

Even on local environments, architecture must reflect enterprise scaling patterns:
- Kafka scale via partitioning and consumer groups
- Spark scale via worker count and executor config
- Isolate heavy pipelines by domain (payments/fraud/locations)
- Profile-based startup to simulate city growth

Suggested profiles:
- small: 1 city, low event rate
- medium: multi-city, moderate event rate
- enterprise-sim: high-throughput stress profile

---

## 15) Cost optimization principles (local + future cloud)

- Start only required compose profiles per stage
- Persist only necessary datasets during active development
- Use synthetic profile sizing to limit unnecessary compute burn
- Reuse shared containers across multiple tasks
- Batch expensive operations (embedding/model retrains) by schedule

---

## 16) How Uber-like companies implement this pattern

- Containerized local dev parity with production architecture principles
- Strong service ownership with common platform contracts
- Observability and incident response built into base stack
- Layered environment definitions (dev/staging/prod equivalents)

Key principle:
Local infrastructure is a development analog of enterprise architecture, not a throwaway setup.

---

## 17) Azure migration equivalent for infrastructure stage

Open-source local component -> Azure equivalent:
- Kafka -> Event Hubs
- Spark cluster -> Azure Databricks
- Lakehouse volumes -> ADLS Gen2 + Delta
- PostgreSQL -> Azure SQL
- MongoDB -> Cosmos DB (Mongo API)
- Weaviate/Chroma -> Azure AI Search (vector)
- Ollama -> Azure OpenAI
- Airflow -> Azure Data Factory
- Prometheus/Grafana -> Azure Monitor + Managed Grafana

Migration note:
Preserve config-driven contracts and topology semantics; migrate runtime adapters and managed service endpoints.

---

## 18) Step-by-step implementation plan (Stage 5)

1. Create docker folder hierarchy and compose layering files.
2. Define shared networks, named volumes, and common env files.
3. Add core service definitions (Kafka, Spark, PostgreSQL, MongoDB, vector DB, Ollama, FastAPI, monitoring).
4. Add service healthchecks and dependency rules.
5. Add bootstrap scripts (Kafka topics, DB schema init, dashboard provisioning).
6. Add config templates for metadata-driven settings.
7. Define resource profiles for small/medium/enterprise-sim.
8. Validate stack startup sequence and service connectivity.
9. Validate persistence (restart without data loss for stateful components).
10. Freeze infra baseline for ingestion and processing stages.

---

## 19) Interview-ready talking points

- We use layered Docker Compose to mirror enterprise architecture while keeping local execution practical.
- Infrastructure is metadata-driven, observable, and contract-aware from day one.
- Windows constraints are handled explicitly with WSL2, named volumes, and deterministic startup.
- The design is cloud-portable with one-to-one Azure service mapping.

---

## 20) Stage 5 exit criteria

Stage 5 is complete when:
- Full Docker topology and service responsibilities are documented.
- Compose layering strategy is approved.
- Persistence, networking, and security baselines are defined.
- Logging, metrics, alerts, and SLA controls are specified.
- Scalability profiles and cost controls are documented.
- Azure-equivalent infrastructure mapping is documented.
