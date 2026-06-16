import os

import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh


st.set_page_config(page_title="Ride AI Assistant", page_icon="🚕", layout="wide")


def normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def call_api(method: str, url: str, payload: dict | None = None, timeout: int = 60):
    try:
        response = requests.request(method=method, url=url, json=payload, timeout=timeout)
        if response.status_code >= 400:
            return None, f"{response.status_code}: {response.text}"
        return response.json(), None
    except Exception as exc:
        return None, str(exc)


def check_service_ready(url: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code < 400:
            return True, f"{response.status_code}"
        return False, f"{response.status_code}: {response.text[:120]}"
    except Exception as exc:
        return False, str(exc)


def render_sidebar() -> str:
    st.sidebar.title("Connection")
    default_api = os.getenv("RIDE_API_URL", "http://localhost:8000")
    default_weaviate = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    default_ollama = os.getenv("OLLAMA_URL", "http://localhost:11434")

    base_url = st.sidebar.text_input("FastAPI Base URL", value=default_api)
    weaviate_url = st.sidebar.text_input("Weaviate URL", value=default_weaviate)
    ollama_url = st.sidebar.text_input("Ollama URL", value=default_ollama)

    auto_refresh_enabled = st.sidebar.toggle("Auto-refresh status", value=False)
    refresh_seconds = st.sidebar.selectbox("Refresh interval (seconds)", options=[10, 30, 60], index=0)

    base_url = normalize_base_url(base_url)
    weaviate_url = normalize_base_url(weaviate_url)
    ollama_url = normalize_base_url(ollama_url)

    if auto_refresh_enabled:
        st_autorefresh(interval=int(refresh_seconds) * 1000, key="system_status_autorefresh")

    st.sidebar.markdown("### System Status")
    api_ok, api_detail = check_service_ready(f"{base_url}/health")
    weaviate_ok, weaviate_detail = check_service_ready(f"{weaviate_url}/v1/.well-known/ready")
    ollama_ok, ollama_detail = check_service_ready(f"{ollama_url}/api/tags")

    st.sidebar.write(f"{'🟢' if api_ok else '🔴'} FastAPI")
    st.sidebar.caption(api_detail)
    st.sidebar.write(f"{'🟢' if weaviate_ok else '🔴'} Weaviate")
    st.sidebar.caption(weaviate_detail)
    st.sidebar.write(f"{'🟢' if ollama_ok else '🔴'} Ollama")
    st.sidebar.caption(ollama_detail)

    if api_ok:
        health, error = call_api("GET", f"{base_url}/health", timeout=20)
        if not error:
            st.sidebar.caption(f"FastAPI environment: {health.get('environment', 'n/a')}")

    st.sidebar.markdown("---")
    st.sidebar.caption("Set RIDE_API_URL, WEAVIATE_URL, OLLAMA_URL env vars to prefill endpoints.")
    return base_url


def render_rag_tab(base_url: str):
    st.subheader("Ride Intelligence Q&A")
    question = st.text_area("Ask a question", height=120, placeholder="Example: Why did cancellations increase in NYC last week?")
    top_k = st.slider("Retrieved sources", min_value=1, max_value=20, value=5)

    if st.button("Ask Assistant", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
            return
        payload = {"question": question.strip(), "top_k": top_k}
        data, error = call_api("POST", f"{base_url}/api/v1/rag/ask", payload=payload, timeout=120)
        if error:
            st.error("RAG request failed")
            st.code(error)
            return

        st.markdown("### Answer")
        st.write(data.get("answer", ""))

        col1, col2 = st.columns(2)
        col1.metric("Retrieved Sources", data.get("retrieved_count", 0))
        col2.metric("Fallback Used", "Yes" if data.get("used_fallback") else "No")

        sources = data.get("sources", [])
        if sources:
            st.markdown("### Sources")
            st.dataframe(sources, use_container_width=True)


def get_feature_defaults(model_name: str) -> dict:
    defaults = {
        "demand_model": {
            "cancelled_trips": 10.0,
            "gross_fare_total": 2500.0,
            "platform_fee_total": 300.0,
            "driver_payout_total": 1900.0,
            "avg_surge_multiplier": 1.2,
        },
        "surge_model": {
            "completed_trips": 120.0,
            "cancelled_trips": 10.0,
            "gross_fare_total": 2500.0,
            "driver_payout_total": 1900.0,
        },
        "fraud_model": {
            "fraud_score": 0.2,
            "final_fare": 35.0,
            "surge_multiplier": 1.1,
            "cancelled_flag": 0.0,
            "completed_flag": 1.0,
        },
        "churn_model": {
            "trip_events": 14.0,
        },
    }
    return defaults[model_name]


def render_prediction_tab(base_url: str):
    st.subheader("Model Prediction")
    model_name = st.selectbox("Model", options=["demand_model", "surge_model", "fraud_model", "churn_model"])

    defaults = get_feature_defaults(model_name)
    features = {}
    cols = st.columns(2)
    for index, (key, value) in enumerate(defaults.items()):
        with cols[index % 2]:
            features[key] = st.number_input(key, value=float(value), step=0.1)

    if st.button("Predict", use_container_width=True):
        payload = {"model_name": model_name, "features": features}
        data, error = call_api("POST", f"{base_url}/api/v1/models/predict", payload=payload)
        if error:
            st.error("Prediction failed")
            st.code(error)
            return

        st.markdown("### Prediction Result")
        if "probability" in data:
            st.metric("Probability", f"{float(data['probability']):.4f}")
        st.metric("Prediction", str(data.get("prediction")))
        st.caption(f"Feature order: {', '.join(data.get('feature_order', []))}")


def render_model_status_tab(base_url: str):
    st.subheader("Model Artifacts Status")
    if st.button("Refresh Status", use_container_width=True):
        data, error = call_api("GET", f"{base_url}/api/v1/models/status")
        if error:
            st.error("Status request failed")
            st.code(error)
            return
        rows = []
        for model_name, details in data.items():
            rows.append({"model_name": model_name, **details})
        st.dataframe(rows, use_container_width=True)


st.title("🚕 Ride-Hailing AI UI")
st.caption("Python UI for RAG assistant and ML inference")

api_base_url = render_sidebar()

tab_rag, tab_predict, tab_status = st.tabs(["RAG Assistant", "Model Prediction", "Model Status"])

with tab_rag:
    render_rag_tab(api_base_url)

with tab_predict:
    render_prediction_tab(api_base_url)

with tab_status:
    render_model_status_tab(api_base_url)
