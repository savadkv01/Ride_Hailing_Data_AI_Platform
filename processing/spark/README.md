# Stage 7 Spark Structured Streaming Runbook

This module implements:
- Bronze: Kafka -> raw Bronze parquet
- Silver: Bronze -> canonical Silver events + quarantine
- Gold: Silver -> city-hourly Gold aggregates

## Prerequisites
- Kafka running in Docker (`kafka:9092` from Spark containers)
- Spark services running via `docker-compose.spark.yml`
- Synthetic producers publishing events

## Job files
- `bronze/bronze_kafka_to_bronze.py`
- `silver/silver_canonical_events.py`
- `gold/gold_city_hourly_metrics.py`
- `config/topic_pipeline_config.json`

## Example commands (inside Spark master container)

### Bronze
```bash
spark-submit /opt/spark/jobs/bronze/bronze_kafka_to_bronze.py \
  --config /opt/spark/jobs/config/topic_pipeline_config.json \
  --bronze-root /opt/lakehouse/bronze/streaming \
  --checkpoint-root /opt/spark/checkpoints/bronze
```

### Silver
```bash
spark-submit /opt/spark/jobs/silver/silver_canonical_events.py \
  --config /opt/spark/jobs/config/topic_pipeline_config.json \
  --bronze-root /opt/lakehouse/bronze/streaming \
  --silver-root /opt/lakehouse/silver \
  --checkpoint-root /opt/spark/checkpoints/silver
```

### Gold
```bash
spark-submit /opt/spark/jobs/gold/gold_city_hourly_metrics.py \
  --silver-root /opt/lakehouse/silver \
  --gold-root /opt/lakehouse/gold \
  --checkpoint-root /opt/spark/checkpoints/gold
```

## Output locations
- Bronze: `lakehouse/bronze/streaming/<bronze_entity>/`
- Silver valid: `lakehouse/silver/canonical_events/`
- Silver quarantine: `lakehouse/silver/quarantine_events/`
- Gold: `lakehouse/gold/city_hourly_metrics/`

## Notes
- Silver pipeline applies event-time watermark and dedup by `event_id`.
- Invalid contract records route to quarantine output.
- Gold aggregates compute city-hour operational and financial KPIs.
