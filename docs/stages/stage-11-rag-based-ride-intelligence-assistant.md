# Stage 11 - RAG-based Ride Intelligence Assistant

## Stage Objective
Implement a retrieval-augmented assistant that answers ride intelligence questions using vectorized corpora and grounded context.

## Why This Stage Matters
- Converts vector indexes into user-facing intelligence.
- Enables explainable answers with source grounding.
- Bridges data platform outputs to operations and support workflows.

## Inputs and Outputs
- Inputs:
  - Weaviate vector class: `RideDocument`
  - Vector corpus generated/indexed in Stage 10
- Outputs:
  - JSON answer payload containing response and retrieval sources
  - Grounded responses to policy, review, support, and fraud-style questions

## Implemented Components
- `rag/config/rag_config.yaml`
- `rag/assistant/ride_intelligence_assistant.py`
- `rag/requirements.txt`
- `rag/README.md`

## Runtime Flow
1. Embed question with configured provider (`hash` or `ollama`).
2. Query Weaviate `nearVector` for top-k context docs.
3. Build grounded prompt with source IDs and snippets.
4. Generate answer with Ollama chat model.
5. Return structured JSON with answer + source references.
6. If generation fails, return extractive fallback answer.

## Local Runbook
1. Install dependencies:
   - `pip install -r rag/requirements.txt`
2. Ensure Weaviate has vectors (Stage 10 completed).
3. Run assistant:
   - `python rag/assistant/ride_intelligence_assistant.py --question "What refund policy applies to service disruption?" --pretty`
4. Inspect output fields:
   - `answer`
   - `retrieved_count`
   - `sources`
   - `used_fallback`

## Azure Mapping
- Weaviate retrieval -> Azure AI Search vector retrieval.
- Ollama generation -> Azure OpenAI chat models.
- Local script -> hosted RAG service behind API Management.

## Exit Criteria (Stage 11)
- RAG assistant can retrieve relevant vector context.
- Grounded answer is generated from retrieved context.
- JSON output includes source metadata for traceability.
- Runbook and config documented.

## Next Stage Preview (Stage 12)
Expose assistant and analytics/model capabilities through FastAPI endpoints.
