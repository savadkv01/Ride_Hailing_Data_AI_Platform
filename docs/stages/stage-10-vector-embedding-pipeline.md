# Stage 10 - Vector Embedding Pipeline

## Stage Objective
Build a metadata-driven vector embedding pipeline that generates corpora, computes embeddings, and indexes vectors into Weaviate for downstream RAG and semantic retrieval.

## Why This Stage Matters
- Enables semantic search beyond relational filtering.
- Supports support-assistant, policy lookup, review intelligence, and fraud investigation RAG use cases.
- Creates reusable vector infrastructure for future APIs.

## Inputs and Outputs
- Inputs:
  - Source catalog index: `config/source_catalog/source_catalog_index.yaml`
  - Vector corpus source configs: `config/source_catalog/synthetic/*_corpus.yaml`
  - Synthetic corpus generators under `ingestion/synthetic/`
- Outputs:
  - Indexed vectors in Weaviate class `RideDocument` (configurable)
  - Pipeline summary with generated/indexed counts

## Implemented Components
- `vector/config/vector_index_config.yaml`
- `vector/pipeline/build_and_index_vectors.py`
- `vector/requirements.txt`
- `vector/README.md`

## Pipeline Design
1. Read vector corpus source configs from source catalog index.
2. Dynamically import generator scripts and synthesize documents.
3. Generate embeddings using provider strategy:
   - `hash` deterministic local baseline
   - `ollama` embedding API (`/api/embeddings`) with fallback option
4. Ensure Weaviate class exists (`vectorizer: none`).
5. Upsert vectorized objects to Weaviate.

## Local Runbook
1. Install dependencies:
   - `pip install -r vector/requirements.txt`
2. Ensure containers are running:
   - Weaviate (`http://localhost:8080`)
   - Optional Ollama (`http://localhost:11434`) for real embeddings
3. Run:
   - `python vector/pipeline/build_and_index_vectors.py`

## Azure Mapping
- Weaviate -> Azure AI Search vector index / Azure Cosmos DB vector capabilities.
- Ollama local embeddings -> Azure OpenAI embeddings.
- Local script -> orchestrated pipeline (ADF/Databricks/Azure ML pipeline).

## Exit Criteria (Stage 10)
- Vector pipeline implemented and runnable.
- Documents generated from metadata-driven corpus configs.
- Embeddings generated and vectors indexed into Weaviate.
- Runbook and configuration documented.

## Next Stage Preview (Stage 11)
Build RAG-based Ride Intelligence Assistant using retrieval from indexed vectors.
