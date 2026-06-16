import json
from datetime import datetime, timezone


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_pipeline_run_audit_table(cur):
    cur.execute("create schema if not exists metadata")
    cur.execute(
        """
        create table if not exists metadata.pipeline_run_audit (
            run_id text primary key,
            pipeline_name text not null,
            stage_name text not null,
            status text not null,
            started_at timestamp not null default current_timestamp,
            ended_at timestamp,
            details jsonb
        )
        """
    )


def create_pipeline_run(cur, run_id, pipeline_name, stage_name, details=None):
    ensure_pipeline_run_audit_table(cur)
    cur.execute(
        """
        insert into metadata.pipeline_run_audit (
            run_id, pipeline_name, stage_name, status, started_at, details
        ) values (%s, %s, %s, %s, %s, %s::jsonb)
        on conflict (run_id) do update
        set
            pipeline_name = excluded.pipeline_name,
            stage_name = excluded.stage_name,
            status = excluded.status,
            started_at = excluded.started_at,
            ended_at = null,
            details = excluded.details
        """,
        (
            run_id,
            pipeline_name,
            stage_name,
            "running",
            utc_now_naive(),
            json.dumps(details or {}),
        ),
    )


def finish_pipeline_run(cur, run_id, status, details=None):
    cur.execute(
        """
        update metadata.pipeline_run_audit
        set
            status = %s,
            ended_at = %s,
            details = coalesce(details, '{}'::jsonb) || (%s::jsonb)
        where run_id = %s
        """,
        (status, utc_now_naive(), json.dumps(details or {}), run_id),
    )