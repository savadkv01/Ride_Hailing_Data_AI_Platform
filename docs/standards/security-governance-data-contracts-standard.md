# Security, Governance & Data Contracts Standard

## Purpose
Define minimum governance and security standards for data ingestion, transformation, ML, and AI pipelines.

## 1) Contract-First Requirement
- Canonical event data must conform to `config/contracts/op_trip_events_contract_v1.json`.
- Any contract-breaking change requires a version bump and approval.
- Contract deprecation window must be at least 30 days.

## 2) Access Control Requirement
- Access rights must follow `config/governance/access_control_policy.yaml`.
- Service identities must use role-mapped permissions only.
- Direct admin access is restricted to platform operators.

## 3) Privacy Requirement
- Raw direct PII is not permitted in canonical, gold, or ML feature zones.
- Use pseudonymous identifiers for rider and driver entities.
- Sensitive credentials must come from environment files or secret managers.

## 4) Audit Requirement
- Every pipeline stage writes run outcomes to `metadata.pipeline_run_audit`.
- Data quality checks write outcomes to `metadata.data_quality_audit`.
- Audit data retention baseline: 90 days.

## 5) Change Governance
- All schema changes require impact review across dbt, ML, vector, and RAG layers.
- Breaking changes require approval from platform, analytics, and security reviewers.
- New city onboarding must pass ingestion, contract, dbt, and DQ gates before scale-up.

## Compliance Checklist
- [ ] Contract validated for all active ingestion paths
- [ ] Access role mapping reviewed and approved
- [ ] PII/pseudonymization checks passed
- [ ] Audit tables receiving run-level records
- [ ] Breaking-change policy followed
