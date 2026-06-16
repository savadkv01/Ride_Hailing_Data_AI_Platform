# Stage 11 - RAG Ride Intelligence Assistant

This module implements a retrieval-augmented assistant over vectors indexed in Weaviate (Stage 10).

## Capabilities
- Embeds user question using Ollama `nomic-embed-text` (768-dim) — falls back to hash if Ollama unavailable
- Retrieves nearest context documents from Weaviate `RideDocument` class
- Builds grounded prompt with source metadata
- Generates answer with Ollama `llama3.2:3b` chat model
- Falls back to extractive answer if LLM is unavailable (`used_fallback: true`)

## Current Configuration (`rag/config/rag_config.yaml`)
| Setting | Value |
|---|---|
| `embedding.provider` | `ollama` |
| `embedding.ollama_embedding_model` | `nomic-embed-text` |
| `generation.ollama_chat_model` | `llama3.2:3b` |
| `weaviate.class_name` | `RideDocument` |
| Weaviate URL | `http://localhost:8080` (host) / `http://weaviate:8080` (Docker) |
| Ollama URL | `http://localhost:11434` (host) / `http://ollama:11434` (Docker) |

## Files
- `rag/config/rag_config.yaml`
- `rag/assistant/ride_intelligence_assistant.py`
- `rag/requirements.txt`

## Prerequisites
- Weaviate running at `http://localhost:8080` with `RideDocument` class populated (50 docs, 768-dim)
- Ollama running with `nomic-embed-text` and `llama3.2:3b` pulled
  ```powershell
  docker exec rh-ollama ollama list
  # Expected: nomic-embed-text, llama3.2:3b
  ```

## Install
```bash
pip install -r rag/requirements.txt
```

## Basic usage
```bash
python rag/assistant/ride_intelligence_assistant.py \
  --question "What do users mention most in reviews about ride quality?" \
  --pretty
```

## Advanced usage
```bash
python rag/assistant/ride_intelligence_assistant.py \
  --question "When are refunds approved according to policy?" \
  --top-k 8 \
  --config rag/config/rag_config.yaml \
  --pretty
```

## Via FastAPI
```powershell
Invoke-RestMethod http://localhost:8000/api/v1/rag/ask -Method Post `
  -ContentType application/json `
  -Body '{"question":"How is surge pricing calculated?","top_k":3}'
```

## Output contract
The script returns JSON with:
- `question`
- `answer` (grounded, bullet-point, with citations `[1]`, `[2]`)
- `used_fallback` (`false` = real Ollama LLM, `true` = extractive fallback)
- `retrieved_count`
- `sources[]` (doc/source metadata and retrieval distance)

## Notes
- To use semantic embeddings, set `embedding.provider: ollama`.
- If Ollama generation is unavailable, `allow_extractive_fallback` keeps assistant usable.
