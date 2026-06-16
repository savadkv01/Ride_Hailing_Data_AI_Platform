# AI UI (Streamlit) – End User Access

This UI provides a browser-based experience for AI use cases without terminal interaction.

## Location
- UI app: `ui/streamlit/app.py`
- Dependencies: `ui/streamlit/requirements.txt`

## Features
- RAG Assistant: ask ride intelligence questions via `/api/v1/rag/ask`
- Model Prediction: run inference for demand/surge/fraud/churn via `/api/v1/models/predict`
- Model Status: check model artifact availability via `/api/v1/models/status`
- System Status panel: live readiness checks for FastAPI, Weaviate, and Ollama
- Auto-refresh toggle for System Status (10/30/60 second interval)

## Run Locally (Windows PowerShell)

```powershell
python -m pip install -r ui/streamlit/requirements.txt
$env:RIDE_API_URL="http://localhost:8000"
streamlit run ui/streamlit/app.py --server.port 8501
```

Open:
- `http://localhost:8501`

## Run with Docker Compose

The UI is wired into `docker/compose/docker-compose.base.yml` as service `streamlit-ui`.

```powershell
docker compose --env-file docker/compose/.env.local \
	-f docker/compose/docker-compose.base.yml up -d streamlit-ui
```

If the base stack is not up yet, start the full stack using your standard compose command and the UI will start with it.

## Prerequisite
- FastAPI service must be running and reachable at `RIDE_API_URL`.
- Default API URL in UI is `http://localhost:8000`.
- Optional endpoint overrides:
	- `WEAVIATE_URL` (default `http://localhost:8080`)
	- `OLLAMA_URL` (default `http://localhost:11434`)

## Typical User Flow
1. Open UI.
2. Confirm API health in sidebar.
3. Use **RAG Assistant** tab for natural-language intelligence queries.
4. Use **Model Prediction** tab for point inference.
5. Use **Model Status** tab to confirm deployed model artifacts.
