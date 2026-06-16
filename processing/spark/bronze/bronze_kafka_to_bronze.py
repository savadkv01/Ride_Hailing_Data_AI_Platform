import argparse
import sys
from pathlib import Path

from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common.pipeline_config import load_pipeline_config
from common.spark_session import build_spark_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 7 Bronze: Kafka -> Bronze parquet")
    parser.add_argument("--config", default="/opt/spark/jobs/config/topic_pipeline_config.json")
    parser.add_argument("--bronze-root", default="/opt/lakehouse/bronze/streaming")
    parser.add_argument("--checkpoint-root", default="/opt/spark/checkpoints/bronze")
    parser.add_argument("--trigger-once", action="store_true", help="Run a bounded trigger-once micro-batch and exit")
    return parser.parse_args()


def start_topic_query(spark, topic_config: dict, kafka_cfg: dict, bronze_root: str, checkpoint_root: str, trigger_once: bool):
    topic_name = topic_config["name"]
    bronze_entity = topic_config["bronze_entity"]

    kafka_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", kafka_cfg["bootstrap_servers"])
        .option("subscribe", topic_name)
        .option("startingOffsets", kafka_cfg.get("starting_offsets", "latest"))
        .option("failOnDataLoss", str(kafka_cfg.get("fail_on_data_loss", False)).lower())
        .load()
    )

    bronze_df = (
        kafka_df.select(
            F.col("topic"),
            F.col("partition"),
            F.col("offset"),
            F.col("timestamp").alias("kafka_timestamp"),
            F.col("timestampType"),
            F.col("key").cast("string").alias("key"),
            F.col("value").cast("string").alias("value"),
            F.current_timestamp().alias("ingestion_time"),
        )
        .withColumn("ingest_date", F.to_date("ingestion_time"))
        .withColumn("bronze_entity", F.lit(bronze_entity))
    )

    writer = (
        bronze_df.writeStream.queryName(f"bronze_{bronze_entity}")
        .format("parquet")
        .option("path", f"{bronze_root}/{bronze_entity}")
        .option("checkpointLocation", f"{checkpoint_root}/{bronze_entity}")
        .partitionBy("ingest_date")
        .outputMode("append")
    )

    if trigger_once:
        writer = writer.trigger(once=True)

    return writer.start()


def main() -> None:
    args = parse_args()
    cfg = load_pipeline_config(args.config)

    spark = build_spark_session("stage7_bronze_kafka_to_bronze")
    spark.sparkContext.setLogLevel("WARN")

    queries = []
    for topic in cfg["topics"]:
        queries.append(
            start_topic_query(
                spark=spark,
                topic_config=topic,
                kafka_cfg=cfg["kafka"],
                bronze_root=args.bronze_root,
                checkpoint_root=args.checkpoint_root,
                trigger_once=args.trigger_once,
            )
        )

    for query in queries:
        query.awaitTermination()


if __name__ == "__main__":
    main()
