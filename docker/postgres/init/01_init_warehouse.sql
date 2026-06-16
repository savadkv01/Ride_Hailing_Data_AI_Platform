CREATE SCHEMA IF NOT EXISTS warehouse;
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS metadata.pipeline_run_audit (
    run_id TEXT PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    details JSONB
);

CREATE TABLE IF NOT EXISTS metadata.data_quality_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    status TEXT NOT NULL,
    violation_count BIGINT DEFAULT 0,
    observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
