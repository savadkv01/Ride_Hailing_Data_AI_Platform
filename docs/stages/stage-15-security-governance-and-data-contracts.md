# Stage 15 – Security, Governance & Data Contracts

## Goal
Establish governance and security controls so data products are trustworthy, access is controlled, and schema evolution is managed through explicit contracts.

## Scope
- Data contract baseline for canonical events
- Access control model for platform personas
- PII handling and retention guardrails
- Contract validation and breaking-change policy

## Outcomes
- Contract-first schema governance for canonical ride events
- Role-based access baseline across schemas and services
- Clear severity matrix for data-quality and contract violations
- Onboarding and change-management checklist for new datasets/cities

## Governance Model

### 1) Data Product Ownership
- `staging.silver_canonical_events` owner: Data Platform team
- `gold.*` owner: Analytics Engineering team
- `ml.*` owner: ML Platform team
- `metadata.*` owner: Platform Reliability team

### 2) Schema Contract Policy
- All producers/normalizers must map to canonical event contract.
- Additive fields allowed with non-breaking defaults.
- Type changes, field removals, and semantic shifts require version bump.
- Contract state tracked as `active`, `deprecated`, or `retired`.

### 3) Access Control Baseline
- Principle: least privilege + environment separation
- Reader roles: BI, ML consumer, support analyst
- Writer roles: ingestion, transform, ML pipeline service identities
- Admin roles limited to platform operators

### 4) Security and Privacy Baseline
- Rider/driver direct identifiers not stored in analytics zones.
- Pseudonymous IDs required in canonical and downstream layers.
- Secrets only from environment files/secret stores; never hardcoded.
- Audit logs retained for pipeline runs and DQ outcomes.

## Data Contract Lifecycle
1. Draft contract
2. Validate sample payloads
3. Approve for `active`
4. Monitor with DQ + contract checks
5. Deprecate with migration window
6. Retire and archive

## Stage 15 Artifacts Added
- Contract baseline: `config/contracts/op_trip_events_contract_v1.json`
- Governance baseline: `config/governance/access_control_policy.yaml`
- Security standard: `docs/standards/security-governance-data-contracts-standard.md`
- Reusable validator: `scripts/contract_validator.py`
- Ingestion wiring:
	- Open-data canonical normalizers enforce contract (`normalize_nyc_to_canonical.py`, `normalize_chicago_to_canonical.py`)
	- Kafka loader validates `trip_completed` subset with configurable mode (`CONTRACT_VALIDATION_MODE=warn|enforce`)

## Exit Criteria for Stage 15
- Canonical event contract exists and is referenced by ingestion workflows
- Role/access matrix defined for core schemas and services
- Breaking-change process documented and enforceable
- Privacy, retention, and audit requirements documented
