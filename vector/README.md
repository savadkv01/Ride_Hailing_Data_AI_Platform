# Stage 10 - Vector Embedding Pipeline

This module builds vector-ready corpora from metadata-driven synthetic sources, computes embeddings using Ollama, and indexes them into Weaviate.

## Inputs
- Source catalog index:
  - `config/source_catalog/source_catalog_index.yaml`
- Vector corpus source configs under:
  - `config/source_catalog/synthetic/*_corpus.yaml`

## Pipeline script
- `vector/pipeline/build_and_index_vectors.py`

## Configuration (`vector/config/vector_index_config.yaml`)

| Setting | Value |
|---|---|
| `embedding.provider` | `ollama` |
| `embedding.ollama_model` | `nomic-embed-text` |
| `embedding.hash_dim` | 256 (used only for fallback) |
| `weaviate.class_name` | `RideDocument` |
| `weaviate.batch_size` | 50 |
| `generation.docs_per_source` | 10 |

## Current state
- **50 documents** indexed across 5 corpus sources: FAQ, reviews, support tickets, policy docs, fraud cases
- **768-dim vectors** from Ollama `nomic-embed-text`
- Weaviate class `RideDocument` created at first run

## Install dependencies
```bash
pip install -r vector/requirements.txt
```

## Run pipeline
```bash
python vector/pipeline/build_and_index_vectors.py
```

## Expected output
```json
{"run_id": "vector-...", "generated_docs": 50, "indexed_docs_total": 50}
```

## Re-indexing after embedding model change
If the embedding model changes (different output dimensions), the Weaviate class must be dropped first:
```powershell
# Drop existing class
Invoke-RestMethod http://localhost:8080/v1/schema/RideDocument -Method Delete
# Re-index
.venv\Scripts\python.exe vector/pipeline/build_and_index_vectors.py
```

## Notes
- Ollama `nomic-embed-text` produces 768-dim vectors. The existing class must have matching dimensions.
- Hash embedding fallback (256-dim) is available via `embedding.provider: hash` when Ollama is not running.
- Hash and Ollama vectors **cannot be mixed in the same Weaviate class** — drop and recreate the class when switching providers.
