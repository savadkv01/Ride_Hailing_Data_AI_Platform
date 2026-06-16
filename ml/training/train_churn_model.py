from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from common import begin_audit_run, finish_audit_run, read_df, save_model, split_xy


def main():
    audit_context = begin_audit_run(
        pipeline_name="ml_train_churn_model",
        stage_name="ml_training",
        details={"model_name": "churn_model"},
    )

    df = read_df(
        """
        select
            churned_7d,
            trip_events
        from ml.feature_rider_churn_daily
        where churned_7d is not null
        """
    )
    if df.empty:
        finish_audit_run(
            audit_context,
            status="success",
            details={"model_name": "churn_model", "rows_read": 0, "note": "no training data"},
        )
        print("no training data for churn model")
        return

    if df["churned_7d"].nunique() < 2:
        finish_audit_run(
            audit_context,
            status="success",
            details={
                "model_name": "churn_model",
                "rows_read": len(df),
                "note": "insufficient class diversity",
            },
        )
        print("insufficient class diversity for churn model")
        return

    try:
        x_train, x_test, y_train, y_test = split_xy(df, "churned_7d")
        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(x_train, y_train)
        probs = model.predict_proba(x_test)[:, 1]
        auc = roc_auc_score(y_test, probs)
        save_model(model, "churn_model")
        finish_audit_run(
            audit_context,
            status="success",
            details={"model_name": "churn_model", "rows_read": len(df), "metric_name": "auc", "metric_value": float(auc)},
        )
        print(f"run_id={audit_context['run_id']} churn_model_auc={auc:.4f}")
    except Exception as exc:
        finish_audit_run(
            audit_context,
            status="failed",
            details={"model_name": "churn_model", "rows_read": len(df)},
            error=exc,
        )
        raise


if __name__ == "__main__":
    main()
