# Stage 12 - FastAPI Platform API Layer

## Stage Objective
Expose unified API endpoints for analytics, model inference, and RAG assistant workflows on top of the platform data and AI layers.

## Why This Stage Matters
- Provides a single integration surface for applications and dashboards.
- Makes warehouse analytics and ML predictions consumable in real time.
- Operationalizes RAG assistant into service endpoints.

## Implemented Endpoints
- `GET /health`
- `GET /metrics`
- `GET /api/v1/analytics/city-daily?limit=30`
- `POST /api/v1/rag/ask`
- `GET /api/v1/models/status`
- `POST /api/v1/models/predict`

## Data/AI Integrations
- PostgreSQL (`gold.mart_city_daily_kpis`) for analytics endpoint.
- Weaviate retrieval for RAG context.
- Ollama generation with fallback extractive response.
- Joblib-loaded model artifacts from `ml/artifacts` for inference.

## Files Updated
- `api/fastapi/app/main.py`
- `api/fastapi/requirements.txt`
- `api/fastapi/Dockerfile`
- `docker/compose/docker-compose.base.yml`

## Local Runbook
1. Rebuild and restart FastAPI service:
   - `docker compose --env-file docker/compose/.env.local -f docker/compose/docker-compose.base.yml up -d --build fastapi`
2. Check health:
   - `GET http://localhost:8000/health`
3. Query analytics:
   - `GET http://localhost:8000/api/v1/analytics/city-daily?limit=5`
4. Ask RAG question:
   - `POST http://localhost:8000/api/v1/rag/ask`
5. Inspect model status and run prediction:
   - `GET http://localhost:8000/api/v1/models/status`
   - `POST http://localhost:8000/api/v1/models/predict`

## Exit Criteria (Stage 12)
- API layer exposes analytics, RAG, and model inference endpoints.
- Endpoints connect to platform services and return structured JSON.
- Container build includes required runtime dependencies and model artifacts.

## Next Stage Preview (Stage 13)
Add deeper observability, structured logs, endpoint SLO metrics, and alert-ready telemetry.
