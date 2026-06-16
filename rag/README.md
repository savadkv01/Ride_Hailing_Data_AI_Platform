# Stage 11 - RAG Ride Intelligence Assistant

This module implements a retrieval-augmented assistant over vectors indexed in Weaviate (Stage 10).

## Capabilities
- Embeds user question (`hash` or `ollama` provider)
- Retrieves nearest context documents from Weaviate
- Builds grounded prompt with source metadata
- Generates answer with Ollama chat model
- Falls back to extractive answer if LLM is unavailable

## Files
- `rag/config/rag_config.yaml`
- `rag/assistant/ride_intelligence_assistant.py`
- `rag/requirements.txt`

## Prerequisites
- Weaviate running at `http://localhost:8080`
- Stage 10 vectors already indexed in class `RideDocument`
- Optional Ollama running at `http://localhost:11434`

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

## Output contract
The script returns JSON with:
- `question`
- `answer`
- `used_fallback`
- `retrieved_count`
- `sources[]` (doc/source metadata and retrieval distance)

## Notes
- To use semantic embeddings, set `embedding.provider: ollama`.
- If Ollama generation is unavailable, `allow_extractive_fallback` keeps assistant usable.
