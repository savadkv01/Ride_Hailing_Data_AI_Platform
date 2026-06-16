# Stage 16 – Azure Enterprise Migration Blueprint

## Goal
Define a production-grade migration path from the current open-source local stack to Azure-native managed services, preserving architecture intent while improving reliability, security, and operability.

## Scope
- Service-by-service Azure mapping
- Migration waves and cutover sequencing
- Data/state migration strategy
- Operational readiness and risk controls

## Current -> Azure Target Pattern

### Data Plane
- Kafka -> Azure Event Hubs (Kafka-compatible endpoint) or Azure Managed Kafka alternative
- Spark standalone -> Azure Databricks / Synapse Spark
- PostgreSQL container -> Azure Database for PostgreSQL Flexible Server
- MongoDB container -> Azure Cosmos DB for MongoDB (or managed MongoDB service)
- Weaviate container -> Azure AI Search (vector) or managed vector DB option
- Ollama local runtime -> Azure OpenAI + managed embedding/chat endpoints

### Control Plane
- Airflow local -> Azure Data Factory / Managed Airflow (where available) / Databricks Workflows
- Docker Compose local runtime -> AKS or Azure Container Apps depending on workload profile
- Prometheus/Grafana local -> Azure Monitor + Managed Grafana

### API & App Layer
- FastAPI container -> Azure App Service / Azure Container Apps / AKS ingress
- Secrets in env files -> Azure Key Vault + managed identity

## Migration Waves

### Wave 1: Foundation (Non-disruptive)
- Provision Azure networking, identity, secrets, and observability baseline
- Replicate environment configuration in IaC-friendly format
- Introduce Key Vault references and managed identity patterns

### Wave 2: Data Core Migration
- Migrate PostgreSQL schemas and data
- Shift event ingress from local Kafka to Event Hubs-compatible endpoint
- Validate staging and dbt parity (row counts + DQ parity)

### Wave 3: Processing and AI Migration
- Move Spark workloads to managed Spark
- Migrate vector indexing and RAG retrieval/generation to Azure-native stack
- Validate ML feature/training parity and model artifact compatibility

### Wave 4: API and Orchestration Cutover
- Deploy API layer to Azure runtime
- Cut orchestration from local Airflow to target orchestrator
- Run blue/green or canary cutover with rollback plan

## Data Migration Rules
- Preserve canonical contract (`op_trip_events`) semantics unchanged.
- Migrate historical data by city/date windows with reconciliation checks.
- Keep dual-write/dual-read window during cutover for critical tables.
- Ensure audit continuity for `metadata.pipeline_run_audit` and `metadata.data_quality_audit`.

## Stage 16 Artifacts Added
- Azure service mapping: `config/migration/azure_service_mapping.yaml`
- Azure migration standard: `docs/standards/azure-migration-governance-standard.md`

## Exit Criteria for Stage 16
- Azure target architecture mapped for every core component
- Migration waves and rollback rules documented
- Security/governance controls mapped to Azure-native equivalents
- Production cutover prerequisites and validation checks defined
