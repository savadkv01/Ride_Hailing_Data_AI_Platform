# Stage 9 - ML Modeling and Feature Pipeline

## Stage Objective
Build baseline ML feature pipelines and train core ride-hailing models for demand, surge, churn, and fraud using curated warehouse tables.

## Why This Stage Matters
- Turns curated `gold` tables into predictive intelligence.
- Establishes repeatable feature engineering and training jobs.
- Provides model artifacts for future serving through APIs.

## Inputs and Outputs
- Input schemas:
  - `gold` (dimensions, facts, marts)
- Output schemas/tables:
  - `ml.feature_demand_city_daily`
  - `ml.feature_fraud_trip`
  - `ml.feature_rider_churn_daily`
- Output artifacts:
  - `ml/artifacts/demand_model.joblib`
  - `ml/artifacts/surge_model.joblib`
  - `ml/artifacts/fraud_model.joblib`
  - `ml/artifacts/churn_model.joblib`

## Implemented Components
- Feature builder:
  - `ml/feature_pipeline/build_feature_tables.py`
- Training modules:
  - `ml/training/train_demand_model.py`
  - `ml/training/train_surge_model.py`
  - `ml/training/train_fraud_model.py`
  - `ml/training/train_churn_model.py`
- Shared training utilities:
  - `ml/training/common.py`
- Config and dependencies:
  - `ml/config/model_config.yaml`
  - `ml/requirements.txt`

## Baseline Modeling Strategy
- Demand and surge: RandomForestRegressor baselines.
- Fraud and churn: RandomForestClassifier baselines.
- Simple holdout split with reproducible random seed.

## Metrics
- Demand/surge: MAE
- Fraud/churn: ROC-AUC

## Local Runbook
1. Install ML dependencies:
   - `pip install -r ml/requirements.txt`
2. Build feature tables:
   - `python ml/feature_pipeline/build_feature_tables.py`
3. Train models:
   - `python ml/training/train_demand_model.py`
   - `python ml/training/train_surge_model.py`
   - `python ml/training/train_fraud_model.py`
   - `python ml/training/train_churn_model.py`

## Azure Mapping
- Local training scripts -> Azure ML pipelines / Databricks ML workflows.
- Local artifacts -> Azure ML Model Registry / Blob-backed model store.
- Local feature tables -> Azure Feature Store patterns.

## Exit Criteria (Stage 9)
- Feature pipeline implemented on top of `gold`.
- Baseline models for demand, surge, churn, fraud trained and saved.
- Re-runnable local runbook documented.

## Next Stage Preview (Stage 10)
Generate embeddings and build vector indexing pipeline for policy/support/review corpora.
