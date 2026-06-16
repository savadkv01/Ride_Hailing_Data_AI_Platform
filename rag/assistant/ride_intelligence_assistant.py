import argparse
import hashlib
import json
import math
import os
import sys
import time
import uuid
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
    payload = {"model": emb_cfg["ollama_embedding_model"], "prompt": text}
    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()
    body = response.json()
    if "embedding" not in body:
        raise RuntimeError(f"Unexpected embedding response: {body}")
    return body["embedding"]


def get_query_embedding(query: str, emb_cfg: dict):
    provider = emb_cfg.get("provider", "hash")
    if provider == "ollama":
        try:
            return ollama_embedding(query, emb_cfg)
        except Exception:
            if emb_cfg.get("allow_fallback_to_hash", True):
                return hash_embedding(query, int(emb_cfg.get("hash_dim", 256)))
            raise
    return hash_embedding(query, int(emb_cfg.get("hash_dim", 256)))


def search_weaviate(query_vector, w_cfg: dict, top_k: int):
    base_url = w_cfg["url"].rstrip("/")
    class_name = w_cfg["class_name"]
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
          targetTable
          text
          _additional {{
            id
            distance
          }}
        }}
      }}
    }}
    """

    response = requests.post(base_url + "/v1/graphql", json={"query": gql}, timeout=60)
    response.raise_for_status()
    body = response.json()

    if "errors" in body:
        raise RuntimeError(f"Weaviate query error: {body['errors']}")

    return body.get("data", {}).get("Get", {}).get(class_name, [])


def build_prompt(question: str, contexts: list):
    context_blocks = []
    for idx, item in enumerate(contexts, start=1):
        context_blocks.append(
            f"[{idx}] source={item.get('sourceId')} type={item.get('sourceType')} city={item.get('cityId')}\n"
            f"text={item.get('text')}"
        )
    context_text = "\n\n".join(context_blocks) if context_blocks else "No context found."

    return (
        "You are a Ride Intelligence Assistant. Answer strictly using the provided context. "
        "If the context is insufficient, say so explicitly.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_text}\n\n"
        "Return concise bullet points and include citation indices like [1], [2]."
    )


def ask_ollama(prompt: str, gen_cfg: dict):
    url = gen_cfg["ollama_url"].rstrip("/") + "/api/generate"
    payload = {
        "model": gen_cfg["ollama_chat_model"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": float(gen_cfg.get("temperature", 0.2))},
    }
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    return body.get("response", "")


def fallback_extractive_answer(question: str, contexts: list):
    if not contexts:
        return "Insufficient context to answer this question."
    top = contexts[0]
    return (
        "Extractive fallback answer (LLM unavailable):\n"
        f"- Most relevant source: {top.get('sourceId')} [{top.get('sourceType')}]\n"
        f"- Evidence: {top.get('text')}"
    )


def run_assistant(question: str, config: dict, top_k: int):
    query_vec = get_query_embedding(question, config["embedding"])
    hits = search_weaviate(query_vec, config["weaviate"], top_k)

    max_docs = int(config["generation"].get("max_context_docs", top_k))
    selected_hits = hits[:max_docs]
    prompt = build_prompt(question, selected_hits)

    answer = ""
    used_fallback = False
    if config["generation"].get("provider", "ollama") == "ollama":
        try:
            answer = ask_ollama(prompt, config["generation"])
        except Exception:
            if config["generation"].get("allow_extractive_fallback", True):
                answer = fallback_extractive_answer(question, selected_hits)
                used_fallback = True
            else:
                raise
    else:
        answer = fallback_extractive_answer(question, selected_hits)
        used_fallback = True

    return {
        "question": question,
        "answer": answer,
        "used_fallback": used_fallback,
        "retrieved_count": len(hits),
        "sources": [
            {
                "docId": item.get("docId"),
                "sourceId": item.get("sourceId"),
                "sourceType": item.get("sourceType"),
                "cityId": item.get("cityId"),
                "distance": item.get("_additional", {}).get("distance"),
            }
            for item in selected_hits
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 11 RAG Ride Intelligence Assistant")
    parser.add_argument("--question", required=True, help="User question for RAG assistant")
    parser.add_argument("--top-k", type=int, default=None, help="Override retrieval top-k")
    parser.add_argument("--config", default="rag/config/rag_config.yaml")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON response")
    return parser.parse_args()


def main():
    run_started = time.perf_counter()
    args = parse_args()
    run_id = f"rag-{uuid.uuid4()}"
    config = load_yaml(Path(args.config))
    weaviate_url = os.getenv("WEAVIATE_URL")
    ollama_url = os.getenv("OLLAMA_URL")
    if weaviate_url:
        config.setdefault("weaviate", {})["url"] = weaviate_url
    if ollama_url:
        config.setdefault("embedding", {})["ollama_url"] = ollama_url
        config.setdefault("generation", {})["ollama_url"] = ollama_url
    top_k = args.top_k or int(config["weaviate"].get("default_top_k", 5))

    audit_conn = get_audit_conn()
    if audit_conn is not None:
        audit_conn.autocommit = False
        with audit_conn.cursor() as cur:
            create_pipeline_run(
                cur,
                run_id=run_id,
                pipeline_name="rag_ride_intelligence_assistant",
                stage_name="rag",
                details={
                    "top_k": int(top_k),
                    "question": args.question,
                },
            )
        audit_conn.commit()

    result = None
    try:
        result = run_assistant(args.question, config, top_k)

        if audit_conn is not None:
            with audit_conn.cursor() as cur:
                finish_pipeline_run(
                    cur,
                    run_id=run_id,
                    status="success",
                    details={
                        "retrieved_count": int(result.get("retrieved_count", 0)),
                        "used_fallback": bool(result.get("used_fallback", False)),
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
                        "duration_seconds": round(time.perf_counter() - run_started, 3),
                        "error": str(exc),
                    },
                )
            audit_conn.commit()
        raise
    finally:
        if audit_conn is not None:
            audit_conn.close()

    result["run_id"] = run_id
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
