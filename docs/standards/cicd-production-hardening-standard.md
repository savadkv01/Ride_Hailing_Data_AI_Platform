# CI/CD & Production Hardening Standard

## Purpose
Define minimum standards for release automation, resilience, and production safety.

## 1) CI Requirements
- Every PR and push to protected branches must run CI.
- CI must include:
  - Python syntax/lint checks
  - YAML/JSON config validation
  - Contract and governance artifact sanity checks
- CI failures block promotion.

## 2) Release Governance
- Promotion path: dev -> staging -> prod.
- Staging and production require manual approvals.
- Production deploy requires validated rollback plan.

## 3) Runtime Resilience
- Canary or blue/green deployment required.
- Error-rate and latency guardrails enforced during rollout.
- Auto-rollback on guardrail breach.

## 4) Security and Compliance
- No plaintext secrets in repository.
- Service identities must use least privilege.
- Release artifacts must preserve auditability of changes.

## 5) Operational Readiness
- On-call rotation and escalation path documented.
- Dashboards and alerts validated before production rollout.
- Pre-release checklist must be completed and archived.

## Compliance Checklist
- [ ] CI passing on target branch
- [ ] Required approvals completed
- [ ] Rollback plan tested
- [ ] Monitoring/alerts validated
- [ ] Security controls verified
