from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor

from common import begin_audit_run, finish_audit_run, read_df, save_model, split_xy


def main():
    audit_context = begin_audit_run(
        pipeline_name="ml_train_surge_model",
        stage_name="ml_training",
        details={"model_name": "surge_model"},
    )

    df = read_df(
        """
        select
            avg_surge_multiplier,
            completed_trips,
            cancelled_trips,
            gross_fare_total,
            driver_payout_total
        from ml.feature_demand_city_daily
        where avg_surge_multiplier is not null
        """
    )
    if df.empty:
        finish_audit_run(
            audit_context,
            status="success",
            details={"model_name": "surge_model", "rows_read": 0, "note": "no training data"},
        )
        print("no training data for surge model")
        return

    try:
        x_train, x_test, y_train, y_test = split_xy(df, "avg_surge_multiplier")
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(x_train, y_train)
        preds = model.predict(x_test)
        mae = mean_absolute_error(y_test, preds)
        save_model(model, "surge_model")
        finish_audit_run(
            audit_context,
            status="success",
            details={"model_name": "surge_model", "rows_read": len(df), "metric_name": "mae", "metric_value": float(mae)},
        )
        print(f"run_id={audit_context['run_id']} surge_model_mae={mae:.4f}")
    except Exception as exc:
        finish_audit_run(
            audit_context,
            status="failed",
            details={"model_name": "surge_model", "rows_read": len(df)},
            error=exc,
        )
        raise


if __name__ == "__main__":
    main()
