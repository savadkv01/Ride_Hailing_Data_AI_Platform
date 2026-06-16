# Stage 10 - Vector Embedding Pipeline

This module builds vector-ready corpora from metadata-driven synthetic sources, computes embeddings, and indexes them into Weaviate.

## Inputs
- Source catalog index:
  - `config/source_catalog/source_catalog_index.yaml`
- Vector corpus source configs under:
  - `config/source_catalog/synthetic/*_corpus.yaml`

## Pipeline script
- `vector/pipeline/build_and_index_vectors.py`

## Configuration
- `vector/config/vector_index_config.yaml`

Key options:
- `embedding.provider`: `hash` (default) or `ollama`
- `embedding.ollama_model`: embedding model name for Ollama
- `weaviate.class_name`: target vector class
- `generation.docs_per_source`: synthetic docs generated per source

## Install dependencies
```bash
pip install -r vector/requirements.txt
```

## Run pipeline
```bash
python vector/pipeline/build_and_index_vectors.py
```

## Expected output
A JSON summary such as:
```json
{"generated_docs": 50, "indexed_docs_total": 50}
```

## Notes
- Hash embeddings provide deterministic local fallback when embedding models are not pulled.
- To use real embeddings, set `embedding.provider: ollama` and ensure Ollama model is available.
