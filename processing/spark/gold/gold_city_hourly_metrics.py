import argparse
import sys
from pathlib import Path

from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common.spark_session import build_spark_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 7 Gold: Silver canonical -> Gold city-hour aggregates")
    parser.add_argument("--silver-root", default="/opt/lakehouse/silver")
    parser.add_argument("--gold-root", default="/opt/lakehouse/gold")
    parser.add_argument("--checkpoint-root", default="/opt/spark/checkpoints/gold")
    parser.add_argument("--trigger-once", action="store_true", help="Run a bounded trigger-once micro-batch and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    spark = build_spark_session("stage7_gold_city_hourly_metrics")
    spark.sparkContext.setLogLevel("WARN")

    silver = spark.readStream.format("parquet").load(f"{args.silver_root}/canonical_events")

    aggregated = (
        silver.withWatermark("event_time", "30 minutes")
        .groupBy(F.window(F.col("event_time"), "1 hour"), F.col("city_id"))
        .agg(
            F.sum(F.when(F.col("event_type") == "trip_completed", 1).otherwise(0)).alias("completed_trips"),
            F.sum(F.when(F.col("event_type") == "trip_cancelled", 1).otherwise(0)).alias("cancelled_trips"),
            F.sum(F.coalesce(F.col("fare_total"), F.lit(0.0))).alias("gross_fare_total"),
            F.sum(F.coalesce(F.col("platform_fee"), F.lit(0.0))).alias("platform_fee_total"),
            F.sum(F.coalesce(F.col("driver_payout"), F.lit(0.0))).alias("driver_payout_total"),
            F.avg(F.coalesce(F.col("surge_multiplier"), F.lit(1.0))).alias("avg_surge_multiplier"),
        )
        .select(
            F.col("city_id"),
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.col("completed_trips"),
            F.col("cancelled_trips"),
            F.col("gross_fare_total"),
            F.col("platform_fee_total"),
            F.col("driver_payout_total"),
            F.col("avg_surge_multiplier"),
            F.to_date(F.col("window.start")).alias("event_date"),
        )
    )

    writer = (
        aggregated.writeStream.queryName("gold_city_hourly_metrics")
        .format("parquet")
        .option("path", f"{args.gold_root}/city_hourly_metrics")
        .option("checkpointLocation", f"{args.checkpoint_root}/city_hourly_metrics")
        .partitionBy("event_date", "city_id")
        .outputMode("append")
    )

    if args.trigger_once:
        writer = writer.trigger(once=True)

    query = writer.start()

    query.awaitTermination()


if __name__ == "__main__":
    main()
