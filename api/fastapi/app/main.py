import hashlib
import json
import logging
import math
import os
import time
from pathlib import Path

import joblib
import psycopg2
import requests
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field

app = FastAPI(title="Ride Hailing Platform API", version="0.1.0")

REQUEST_COUNT = Counter(
    "fastapi_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "fastapi_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

START_TIME = time.time()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
LOGGER = logging.getLogger("ride_hailing_fastapi")


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("x-request-id") or f"req-{int(time.time() * 1000)}"
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        latency_seconds = time.perf_counter() - start
        endpoint = request.url.path
        method = request.method
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency_seconds)

        LOGGER.info(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "event": "api_request",
                    "request_id": request_id,
                    "method": method,
                    "path": endpoint,
                    "status": status_code,
                    "latency_ms": round(latency_seconds * 1000, 2),
                    "client": request.client.host if request.client else None,
                }
            )
        )


class RagAskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)


class ModelPredictRequest(BaseModel):
    model_name: str
    features: dict


def get_postgres_conn():
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    return psycopg2.connect(
        host=os.getenv("PGHOST", os.getenv("POSTGRES_HOST", "localhost")),
        port=int(os.getenv("PGPORT", os.getenv("POSTGRES_PORT", "5432"))),
        dbname=os.getenv("PGDATABASE", os.getenv("POSTGRES_DB", "ride_warehouse")),
        user=os.getenv("PGUSER", os.getenv("POSTGRES_USER", "ride_admin")),
        password=os.getenv("PGPASSWORD", os.getenv("POSTGRES_PASSWORD", "ride_password")),
    )


def hash_embedding(text: str, dim: int = 256):
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = -1.0 if ((h >> 1) & 1) else 1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def search_weaviate(question: str, top_k: int):
    base_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080").rstrip("/")
    class_name = os.getenv("WEAVIATE_CLASS", "RideDocument")
    query_vector = hash_embedding(question, int(os.getenv("RAG_HASH_DIM", "256")))
    vector_text = ", ".join(str(round(v, 8)) for v in query_vector)

    gql = f"""
    {{
      Get {{
        {class_name}(
          nearVector: {{ vector: [{vector_text}] }}
          limit: {top_k}
        ) {{
          docId
          sourceId
          sourceType
          cityId
          text
          _additional {{ distance }}
        }}
      }}
    }}
    """

    resp = requests.post(base_url + "/v1/graphql", json={"query": gql}, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])

    return body.get("data", {}).get("Get", {}).get(class_name, [])


def generate_rag_answer(question: str, sources: list):
    if not sources:
        return {
            "answer": "Insufficient context to answer this question.",
            "used_fallback": True,
        }

    ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")
    model = os.getenv("RAG_CHAT_MODEL", "llama3.2:3b")

    context_lines = []
    for index, source in enumerate(sources, start=1):
        context_lines.append(
            f"[{index}] source={source.get('sourceId')} type={source.get('sourceType')} city={source.get('cityId')}\n"
            f"text={source.get('text')}"
        )

    prompt = (
        "You are a Ride Intelligence Assistant. Answer only from the provided context. "
        "If the context is insufficient, say so.\n\n"
        f"Question: {question}\n\n"
        "Context:\n"
        + "\n\n".join(context_lines)
        + "\n\nReturn concise bullets with citations like [1], [2]."
    )

    try:
        resp = requests.post(
            ollama_url + "/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90,
        )
        resp.raise_for_status()
        payload = resp.json()
        return {"answer": payload.get("response", ""), "used_fallback": False}
    except Exception:
        top = sources[0]
        fallback = (
            "Extractive fallback answer (LLM unavailable):\n"
            f"- Most relevant source: {top.get('sourceId')} [{top.get('sourceType')}]\n"
            f"- Evidence: {top.get('text')}"
        )
        return {"answer": fallback, "used_fallback": True}


def resolve_model_path(model_name: str) -> Path:
    models_root = Path(os.getenv("MODEL_ARTIFACTS_DIR", "/app/ml/artifacts"))
    return models_root / f"{model_name}.joblib"


def model_feature_order(model_name: str):
    mapping = {
        "demand_model": [
            "cancelled_trips",
            "gross_fare_total",
            "platform_fee_total",
            "driver_payout_total",
            "avg_surge_multiplier",
        ],
        "surge_model": [
            "completed_trips",
            "cancelled_trips",
            "gross_fare_total",
            "driver_payout_total",
        ],
        "fraud_model": [
            "fraud_score",
            "final_fare",
            "surge_multiplier",
            "cancelled_flag",
            "completed_flag",
        ],
        "churn_model": [
            "trip_events",
        ],
    }
    if model_name not in mapping:
        raise ValueError(f"Unsupported model_name: {model_name}")
    return mapping[model_name]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "ride-hailing-fastapi",
        "environment": os.getenv("APP_ENV", "local"),
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }


@app.get("/")
def root() -> dict:
    return {
        "message": "Ride-Hailing Data & AI Platform API",
        "status": "running",
    }


@app.get("/api/v1/analytics/city-daily")
def analytics_city_daily(limit: int = 30) -> dict:
    safe_limit = max(1, min(limit, 365))
    sql = (
        "select event_date, city_id, completed_trips, cancelled_trips, gross_fare_total, "
        "platform_fee_total, driver_payout_total, avg_surge_multiplier "
        "from gold.mart_city_daily_kpis "
        "order by event_date desc, city_id asc "
        f"limit {safe_limit}"
    )

    try:
        conn = get_postgres_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analytics query failed: {exc}")

    return {
        "row_count": len(rows),
        "rows": [dict(zip(cols, row)) for row in rows],
    }


@app.post("/api/v1/rag/ask")
def rag_ask(payload: RagAskRequest) -> dict:
    try:
        sources = search_weaviate(payload.question, payload.top_k)
        answer = generate_rag_answer(payload.question, sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG request failed: {exc}")

    return {
        "question": payload.question,
        "answer": answer["answer"],
        "used_fallback": answer["used_fallback"],
        "retrieved_count": len(sources),
        "sources": [
            {
                "docId": item.get("docId"),
                "sourceId": item.get("sourceId"),
                "sourceType": item.get("sourceType"),
                "cityId": item.get("cityId"),
                "distance": item.get("_additional", {}).get("distance"),
            }
            for item in sources
        ],
    }


@app.get("/api/v1/models/status")
def model_status() -> dict:
    model_names = ["demand_model", "surge_model", "fraud_model", "churn_model"]
    status = {}
    for model_name in model_names:
        model_path = resolve_model_path(model_name)
        status[model_name] = {
            "exists": model_path.exists(),
            "path": str(model_path),
        }
    return status


@app.post("/api/v1/models/predict")
def model_predict(payload: ModelPredictRequest) -> dict:
    model_name = payload.model_name.strip()

    try:
        feature_order = model_feature_order(model_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    model_path = resolve_model_path(model_name)
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model artifact not found: {model_path}")

    try:
        model = joblib.load(model_path)
        vector = [[float(payload.features.get(name, 0.0)) for name in feature_order]]

        if model_name in {"fraud_model", "churn_model"} and hasattr(model, "predict_proba"):
            proba = float(model.predict_proba(vector)[0][1])
            pred = int(proba >= 0.5)
            return {
                "model_name": model_name,
                "prediction": pred,
                "probability": proba,
                "feature_order": feature_order,
            }

        pred_value = float(model.predict(vector)[0])
        return {
            "model_name": model_name,
            "prediction": pred_value,
            "feature_order": feature_order,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")


@app.get("/api/v1/monitoring/data-quality/latest")
def data_quality_latest(limit: int = 20) -> dict:
    safe_limit = max(1, min(limit, 200))
    sql = (
        "select run_id, rule_id, target_entity, status, violation_count, observed_at "
        "from metadata.data_quality_audit "
        "order by observed_at desc "
        f"limit {safe_limit}"
    )

    try:
        conn = get_postgres_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Data quality query failed: {exc}")

    return {
        "row_count": len(rows),
        "rows": [dict(zip(cols, row)) for row in rows],
    }


@app.get("/api/v1/monitoring/pipeline-runs/latest")
def pipeline_runs_latest(limit: int = 20) -> dict:
    safe_limit = max(1, min(limit, 200))
    sql = (
        "select run_id, pipeline_name, stage_name, status, started_at, ended_at, details "
        "from metadata.pipeline_run_audit "
        "order by started_at desc "
        f"limit {safe_limit}"
    )

    try:
        conn = get_postgres_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline run query failed: {exc}")

    return {
        "row_count": len(rows),
        "rows": [dict(zip(cols, row)) for row in rows],
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
