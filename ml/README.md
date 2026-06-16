# Stage 9 - ML Modeling and Feature Pipeline

This module provides baseline feature engineering and model training for:
- demand prediction
- surge multiplier prediction
- rider churn classification
- fraud risk classification

## Prerequisites
- PostgreSQL is running and contains Stage 8 `gold` schema tables.
- Python environment has ML dependencies installed:
  - `pip install -r ml/requirements.txt`

## Build feature tables
```bash
python ml/feature_pipeline/build_feature_tables.py
```

This creates feature tables in schema `ml`:
- `ml.feature_demand_city_daily`
- `ml.feature_fraud_trip`
- `ml.feature_rider_churn_daily`

## Train baseline models
```bash
python ml/training/train_demand_model.py
python ml/training/train_surge_model.py
python ml/training/train_fraud_model.py
python ml/training/train_churn_model.py
```

## Artifacts
Models are saved under:
- `ml/artifacts/demand_model.joblib`
- `ml/artifacts/surge_model.joblib`
- `ml/artifacts/fraud_model.joblib`
- `ml/artifacts/churn_model.joblib`

## Notes
- These are baseline models for local development.
- Stage 10+ can add model registry, retraining schedules, and feature store integration.
- Stage 13 observability now logs ML feature/training runs in `metadata.pipeline_run_audit` with status, timing, and metrics.
