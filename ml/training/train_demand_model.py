from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor

from common import begin_audit_run, finish_audit_run, read_df, save_model, split_xy


def main():
    audit_context = begin_audit_run(
        pipeline_name="ml_train_demand_model",
        stage_name="ml_training",
        details={"model_name": "demand_model"},
    )

    df = read_df(
        """
        select
            completed_trips,
            cancelled_trips,
            gross_fare_total,
            platform_fee_total,
            driver_payout_total,
            avg_surge_multiplier
        from ml.feature_demand_city_daily
        where completed_trips is not null
        """
    )
    if df.empty:
        finish_audit_run(
            audit_context,
            status="success",
            details={"model_name": "demand_model", "rows_read": 0, "note": "no training data"},
        )
        print("no training data for demand model")
        return

    try:
        x_train, x_test, y_train, y_test = split_xy(df, "completed_trips")
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(x_train, y_train)
        preds = model.predict(x_test)
        mae = mean_absolute_error(y_test, preds)
        save_model(model, "demand_model")
        finish_audit_run(
            audit_context,
            status="success",
            details={"model_name": "demand_model", "rows_read": len(df), "metric_name": "mae", "metric_value": float(mae)},
        )
        print(f"run_id={audit_context['run_id']} demand_model_mae={mae:.4f}")
    except Exception as exc:
        finish_audit_run(
            audit_context,
            status="failed",
            details={"model_name": "demand_model", "rows_read": len(df)},
            error=exc,
        )
        raise


if __name__ == "__main__":
    main()
