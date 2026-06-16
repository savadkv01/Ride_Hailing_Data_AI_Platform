# Azure Migration Governance Standard

## Purpose
Define governance and risk controls for migrating the platform from local open-source infrastructure to Azure-native services.

## 1) Migration Principles
- Preserve canonical data contract semantics during migration.
- Prefer managed services for reliability and operational reduction.
- Enforce least privilege and secretless auth where possible.
- Require reversible cutovers with documented rollback.

## 2) Security and Identity Requirements
- All service credentials stored in Azure Key Vault.
- Service-to-service authentication should use Managed Identity.
- Production data paths must use private networking controls.
- Public endpoints require explicit approval and monitoring.

## 3) Data Integrity Requirements
- Every migration wave must pass parity validation:
  - row counts
  - key aggregates
  - contract compliance
  - DQ pass thresholds
- Audit tables must remain continuous and queryable after cutover.

## 4) Operational Requirements
- Observability parity required before production cutover.
- SLOs must be defined and measured on Azure target stack.
- Incident runbooks and rollback playbooks must be tested.

## 5) Change Control
- Production cutover requires approval from:
  - Platform owner
  - Data governance owner
  - Security reviewer
- Breaking architecture changes require documented impact analysis.

## Compliance Checklist
- [ ] Azure service mapping approved
- [ ] Identity/secret model validated
- [ ] Data parity checks passed
- [ ] Observability dashboards/alerts active
- [ ] Rollback procedure tested
