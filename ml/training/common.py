import os
from pathlib import Path
import sys
import time
import uuid

import joblib
import pandas as pd
import psycopg2
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.env_loader import auto_load_env, postgres_connection_kwargs
from scripts.pipeline_audit import create_pipeline_run, finish_pipeline_run

auto_load_env(project_root=PROJECT_ROOT)


def get_conn():
    return psycopg2.connect(**postgres_connection_kwargs())


def read_df(sql: str) -> pd.DataFrame:
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def split_xy(df: pd.DataFrame, target: str):
    x = df.drop(columns=[target])
    y = df[target]
    return train_test_split(x, y, test_size=0.2, random_state=42)


def save_model(model, model_name: str):
    out_dir = Path("ml/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / f"{model_name}.joblib")


def begin_audit_run(pipeline_name: str, stage_name: str, details: dict | None = None):
    run_id = f"{stage_name}-{uuid.uuid4()}"
    started_perf = time.perf_counter()

    try:
        conn = get_conn()
        conn.autocommit = False
        with conn.cursor() as cur:
            create_pipeline_run(
                cur,
                run_id=run_id,
                pipeline_name=pipeline_name,
                stage_name=stage_name,
                details=details or {},
            )
        conn.commit()
        return {"run_id": run_id, "conn": conn, "started_perf": started_perf}
    except Exception:
        return {"run_id": run_id, "conn": None, "started_perf": started_perf}


def finish_audit_run(context: dict, status: str, details: dict | None = None, error: Exception | None = None):
    conn = context.get("conn")
    if conn is None:
        return

    payload = dict(details or {})
    payload["duration_seconds"] = round(time.perf_counter() - context["started_perf"], 3)
    if error is not None:
        payload["error"] = str(error)

    try:
        with conn.cursor() as cur:
            finish_pipeline_run(
                cur,
                run_id=context["run_id"],
                status=status,
                details=payload,
            )
        conn.commit()
    finally:
        conn.close()
