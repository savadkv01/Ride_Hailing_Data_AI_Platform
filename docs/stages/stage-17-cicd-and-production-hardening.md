# Stage 17 – CI/CD & Production Hardening

## Goal
Operationalize the platform with repeatable build/test/release controls, resilience safeguards, and production-grade readiness checks.

## Scope
- CI workflow baseline for code quality and safety gates
- Release governance and deployment promotion policy
- Production hardening controls (rollback, SLO, incident response)
- Runbook/checklist for pre-production and production cutover

## Outcomes
- Standardized CI pipeline for validation on every change
- Clear release stages (`dev` -> `staging` -> `prod`) with promotion gates
- Explicit rollback and resilience expectations
- Repeatable production readiness checklist

## CI/CD Baseline

### 1) Continuous Integration
- Trigger on push/PR to main branches
- Lint and syntax checks for Python and YAML/JSON configs
- Contract/governance artifact validation in CI
- Fail-fast on critical quality/security violations

### 2) Release Promotion Model
- `dev`: rapid iteration, non-blocking exploratory tests
- `staging`: full integration tests + data contract/DQ checks
- `prod`: gated promotion with approval + rollback plan

### 3) Deployment Strategy
- Prefer blue/green or canary rollout
- Track health and key KPIs during rollout window
- Automatic rollback if error rate/SLO breach threshold is crossed

## Production Hardening Controls
- Availability and latency SLO definitions per critical service
- Dependency health checks (DB, message bus, vector store, LLM runtime)
- Backup/restore plan for warehouse metadata and critical datasets
- Disaster recovery objective targets (RTO/RPO)
- Security posture checks in release checklist (secrets, access, audit)

## Stage 17 Artifacts Added
- CI workflow template: `.github/workflows/ci.yml`
- Release/hardening policy: `config/release/production_hardening_policy.yaml`
- Operational standard: `docs/standards/cicd-production-hardening-standard.md`
- Release readiness checklist: `docs/operations/release-readiness-checklist.md`

## Exit Criteria for Stage 17
- CI pipeline exists and enforces baseline quality checks
- Promotion policy documented with approval and rollback requirements
- Production readiness checklist documented and usable
- Resilience/security controls clearly defined for go-live
