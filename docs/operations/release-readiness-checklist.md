# Release Readiness Checklist

Use this checklist before staging/prod cutover.

## Change Summary
- Release version/tag:
- Scope:
- Risk level:
- Owner:

## Pre-Release Gates
- [ ] CI workflow passed on target branch
- [ ] Data contract validations passed
- [ ] Data quality checks passed
- [ ] Security review completed
- [ ] Migration impact assessed (if applicable)

## Runtime Readiness
- [ ] Required services healthy (API, DB, messaging, vector, orchestration)
- [ ] Dashboards verified (latency, error rate, throughput)
- [ ] Alerts verified and routed to on-call
- [ ] Capacity assumptions validated

## Rollout Plan
- Strategy: [ ] Canary  [ ] Blue/Green
- [ ] Rollout steps documented
- [ ] Rollback trigger thresholds documented
- [ ] Rollback owner assigned

## Post-Release Validation
- [ ] Smoke tests passed
- [ ] Pipeline run audit healthy
- [ ] DQ audit healthy
- [ ] Business KPI sanity checks completed

## Sign-Off
- Platform owner:
- Data governance owner:
- SRE owner:
- Date:
