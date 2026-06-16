import argparse
import sys
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.types import (
    IntegerType,
    LongType,
    MapType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common.pipeline_config import load_pipeline_config
from common.spark_session import build_spark_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 7 Silver: Bronze raw -> Silver canonical")
    parser.add_argument("--config", default="/opt/spark/jobs/config/topic_pipeline_config.json")
    parser.add_argument("--bronze-root", default="/opt/lakehouse/bronze/streaming")
    parser.add_argument("--silver-root", default="/opt/lakehouse/silver")
    parser.add_argument("--checkpoint-root", default="/opt/spark/checkpoints/silver")
    parser.add_argument("--trigger-once", action="store_true", help="Run a bounded trigger-once micro-batch and exit")
    return parser.parse_args()


def to_double(payload_col, key: str):
    return F.col(payload_col).getItem(key).cast("double")


def to_long(payload_col, key: str):
    return F.col(payload_col).getItem(key).cast("long")


def to_ts(payload_col, key: str):
    return F.to_timestamp(F.col(payload_col).getItem(key))


def main() -> None:
    args = parse_args()
    cfg = load_pipeline_config(args.config)

    spark = build_spark_session("stage7_silver_canonical_events")
    spark.sparkContext.setLogLevel("WARN")

    # Explicit schema avoids Hive partition inference assertion in ParquetFileFormat
    # when reading Bronze parquet written with ingest_date partitioning via wildcard path.
    bronze_schema = StructType([
        StructField("topic", StringType(), True),
        StructField("partition", IntegerType(), True),
        StructField("offset", LongType(), True),
        StructField("kafka_timestamp", TimestampType(), True),
        StructField("timestampType", IntegerType(), True),
        StructField("key", StringType(), True),
        StructField("value", StringType(), True),
        StructField("ingestion_time", TimestampType(), True),
        StructField("bronze_entity", StringType(), True),
    ])

    bronze_df = (
        spark.readStream.format("parquet")
        .schema(bronze_schema)
        .option("recursiveFileLookup", "true")
        .load(args.bronze_root)
    )

    parsed = bronze_df.withColumn("payload", F.from_json(F.col("value"), MapType(StringType(), StringType())))

    canonical = (
        parsed.select(
            F.col("topic").alias("source_topic"),
            F.col("bronze_entity"),
            F.col("ingestion_time"),
            F.col("payload").getItem("event_id").alias("event_id"),
            F.col("payload").getItem("event_type").alias("event_type"),
            to_ts("payload", "event_time").alias("event_time"),
            F.col("payload").getItem("trip_id").alias("trip_id"),
            F.col("payload").getItem("rider_id").alias("rider_id"),
            F.col("payload").getItem("driver_id").alias("driver_id"),
            F.col("payload").getItem("vehicle_id").alias("vehicle_id"),
            F.col("payload").getItem("city_id").alias("city_id"),
            F.col("payload").getItem("payment_id").alias("payment_id"),
            F.col("payload").getItem("refund_id").alias("refund_id"),
            F.col("payload").getItem("review_id").alias("review_id"),
            F.col("payload").getItem("support_ticket_id").alias("support_ticket_id"),
            F.col("payload").getItem("fraud_case_id").alias("fraud_case_id"),
            to_double("payload", "fare_total").alias("fare_total"),
            to_double("payload", "surge_multiplier").alias("surge_multiplier"),
            to_double("payload", "promotion_amount").alias("promotion_amount"),
            to_double("payload", "platform_fee").alias("platform_fee"),
            to_double("payload", "driver_payout").alias("driver_payout"),
            to_double("payload", "amount").alias("payment_amount"),
            to_double("payload", "refund_amount").alias("refund_amount"),
            to_double("payload", "rating_value").alias("rating_value"),
            to_double("payload", "fraud_score").alias("fraud_score"),
            to_double("payload", "latitude").alias("latitude"),
            to_double("payload", "longitude").alias("longitude"),
            to_double("payload", "avg_surge_multiplier").alias("avg_surge_multiplier"),
            to_long("payload", "requested_trips").alias("requested_trips"),
            to_long("payload", "completed_trips").alias("completed_trips"),
            to_long("payload", "active_drivers").alias("active_drivers"),
            F.col("payload").getItem("source_system").alias("source_system"),
            F.col("payload").getItem("schema_version").alias("schema_version"),
            F.col("value").alias("raw_payload"),
        )
        .withColumn("event_date", F.to_date("event_time"))
    )

    valid = (
        canonical.withWatermark("event_time", cfg["quality"]["watermark"])
        .dropDuplicates(["event_id"])
        .filter(F.col("event_id").isNotNull() & F.col("event_time").isNotNull() & F.col("city_id").isNotNull())
    )

    invalid = canonical.filter(
        F.col("event_id").isNull() | F.col("event_time").isNull() | F.col("city_id").isNull()
    )

    valid_writer = (
        valid.writeStream.queryName("silver_canonical_events")
        .format("parquet")
        .option("path", f"{args.silver_root}/canonical_events")
        .option("checkpointLocation", f"{args.checkpoint_root}/canonical_events")
        .partitionBy("event_date", "city_id")
        .outputMode("append")
    )
    invalid_writer = (
        invalid.writeStream.queryName("silver_quarantine_events")
        .format("parquet")
        .option("path", f"{args.silver_root}/quarantine_events")
        .option("checkpointLocation", f"{args.checkpoint_root}/quarantine_events")
        .outputMode("append")
    )

    if args.trigger_once:
        valid_writer = valid_writer.trigger(once=True)
        invalid_writer = invalid_writer.trigger(once=True)

    valid_query = valid_writer.start()
    invalid_query = invalid_writer.start()

    valid_query.awaitTermination()
    invalid_query.awaitTermination()


if __name__ == "__main__":
    main()
