import hashlib
import importlib
import json
import math
import os
import time
import uuid
import sys
from pathlib import Path

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.env_loader import auto_load_env, postgres_connection_kwargs
from scripts.pipeline_audit import create_pipeline_run, finish_pipeline_run

auto_load_env(project_root=PROJECT_ROOT)


def get_audit_conn():
    try:
        import psycopg2
    except ImportError:
        return None

    try:
        dsn = os.getenv("POSTGRES_DSN")
        if dsn:
            return psycopg2.connect(dsn)

        return psycopg2.connect(**postgres_connection_kwargs())
    except Exception:
        return None


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def script_path_to_module(script_path: str) -> str:
    return script_path.replace("/", ".").replace("\\", ".").replace(".py", "")


def generate_documents(root: Path, config: dict):
    index_path = root / config["source_catalog_index"]
    index_cfg = load_yaml(index_path)
    source_paths = index_cfg.get(config["vector_sources_key"], [])
    docs_per_source = int(config["generation"]["docs_per_source"])

    documents = []
    for source_path in source_paths:
        src_cfg = load_yaml(root / source_path)
        module_name = script_path_to_module(src_cfg["generator_script"])
        module = importlib.import_module(module_name)

        for _ in range(docs_per_source):
            payload = module.generate()
            text = payload.get("text")
            if not text:
                continue
            documents.append(
                {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{src_cfg['source_id']}::{payload.get('doc_id', uuid.uuid4())}")),
                    "source_id": src_cfg["source_id"],
                    "target_table": src_cfg.get("target_table", "unknown"),
                    "source_type": payload.get("source_type", "unknown"),
                    "city_id": payload.get("city_id", "unknown"),
                    "doc_id": payload.get("doc_id", "unknown"),
                    "text": text,
                }
            )
    return documents


def hash_embedding(text: str, dim: int):
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


def ollama_embedding(text: str, emb_cfg: dict):
    url = emb_cfg["ollama_url"].rstrip("/") + "/api/embeddings"
    body = {"model": emb_cfg["ollama_model"], "prompt": text}
    resp = requests.post(url, json=body, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    if "embedding" not in data:
        raise RuntimeError(f"Unexpected Ollama embedding response: {data}")
    return data["embedding"]


def embed_documents(documents, emb_cfg: dict):
    provider = emb_cfg.get("provider", "hash")
    vectors = []

    for doc in documents:
        text = doc["text"]
        if provider == "ollama":
            try:
                vector = ollama_embedding(text, emb_cfg)
            except Exception:
                if emb_cfg.get("allow_fallback_to_hash", True):
                    vector = hash_embedding(text, int(emb_cfg.get("hash_dim", 256)))
                else:
                    raise
        else:
            vector = hash_embedding(text, int(emb_cfg.get("hash_dim", 256)))

        vectors.append((doc, vector))

    return vectors


def ensure_weaviate_class(base_url: str, class_name: str):
    schema_url = base_url.rstrip("/") + "/v1/schema"
    response = requests.get(schema_url, timeout=30)
    response.raise_for_status()
    classes = response.json().get("classes", [])
    if any(entry.get("class") == class_name for entry in classes):
        return

    body = {
        "class": class_name,
        "vectorizer": "none",
        "properties": [
            {"name": "docId", "dataType": ["text"]},
            {"name": "sourceId", "dataType": ["text"]},
            {"name": "sourceType", "dataType": ["text"]},
            {"name": "cityId", "dataType": ["text"]},
            {"name": "targetTable", "dataType": ["text"]},
            {"name": "text", "dataType": ["text"]},
        ],
    }
    create_resp = requests.post(schema_url, json=body, timeout=30)
    create_resp.raise_for_status()


def index_vectors(items, w_cfg: dict):
    base_url = w_cfg["url"].rstrip("/")
    class_name = w_cfg["class_name"]
    batch_size = int(w_cfg.get("batch_size", 50))

    ensure_weaviate_class(base_url, class_name)

    for i in range(0, len(items), batch_size):
        chunk = items[i : i + batch_size]
        for doc, vector in chunk:
            body = {
                "class": class_name,
                "id": doc["id"],
                "properties": {
                    "docId": doc["doc_id"],
                    "sourceId": doc["source_id"],
                    "sourceType": doc["source_type"],
                    "cityId": doc["city_id"],
                    "targetTable": doc["target_table"],
                    "text": doc["text"],
                },
                "vector": vector,
            }
            resp = requests.post(base_url + "/v1/objects", json=body, timeout=30)
            if resp.status_code not in (200, 201, 422):
                resp.raise_for_status()


def get_object_count(base_url: str, class_name: str):
    resp = requests.get(
        base_url.rstrip("/") + f"/v1/objects?class={class_name}&limit=10000",
        timeout=60,
    )
    resp.raise_for_status()
    return len(resp.json().get("objects", []))


def main():
    run_started = time.perf_counter()
    run_id = f"vector-{uuid.uuid4()}"
    root = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
    cfg_path = root / "vector/config/vector_index_config.yaml"
    config = load_yaml(cfg_path)

    weaviate_url = os.getenv("WEAVIATE_URL")
    ollama_url = os.getenv("OLLAMA_URL")
    if weaviate_url:
        config.setdefault("weaviate", {})["url"] = weaviate_url
    if ollama_url:
        config.setdefault("embedding", {})["ollama_url"] = ollama_url

    audit_conn = get_audit_conn()
    if audit_conn is not None:
        audit_conn.autocommit = False
        with audit_conn.cursor() as cur:
            create_pipeline_run(
                cur,
                run_id=run_id,
                pipeline_name="vector_index_builder",
                stage_name="vector",
                details={
                    "docs_per_source": int(config["generation"]["docs_per_source"]),
                    "embedding_provider": config["embedding"].get("provider", "hash"),
                },
            )
        audit_conn.commit()

    docs = []
    embedded = []
    count = 0

    try:
        docs = generate_documents(root, config)
        embedded = embed_documents(docs, config["embedding"])
        index_vectors(embedded, config["weaviate"])

        count = get_object_count(config["weaviate"]["url"], config["weaviate"]["class_name"])

        if audit_conn is not None:
            with audit_conn.cursor() as cur:
                finish_pipeline_run(
                    cur,
                    run_id=run_id,
                    status="success",
                    details={
                        "generated_docs": len(docs),
                        "embedded_docs": len(embedded),
                        "indexed_docs_total": count,
                        "duration_seconds": round(time.perf_counter() - run_started, 3),
                    },
                )
            audit_conn.commit()
    except Exception as exc:
        if audit_conn is not None:
            with audit_conn.cursor() as cur:
                finish_pipeline_run(
                    cur,
                    run_id=run_id,
                    status="failed",
                    details={
                        "generated_docs": len(docs),
                        "embedded_docs": len(embedded),
                        "duration_seconds": round(time.perf_counter() - run_started, 3),
                        "error": str(exc),
                    },
                )
            audit_conn.commit()
        raise
    finally:
        if audit_conn is not None:
            audit_conn.close()

    print(json.dumps({"run_id": run_id, "generated_docs": len(docs), "indexed_docs_total": count}))


if __name__ == "__main__":
    main()
