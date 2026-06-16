#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_SERVER=${BOOTSTRAP_SERVER:-kafka:9092}
PARTITIONS=${PARTITIONS:-6}
REPLICATION=${REPLICATION:-1}

if command -v kafka-topics >/dev/null 2>&1; then
  KAFKA_TOPICS_CMD="kafka-topics"
elif command -v kafka-topics.sh >/dev/null 2>&1; then
  KAFKA_TOPICS_CMD="kafka-topics.sh"
else
  echo "No kafka-topics command found in PATH"
  exit 1
fi

TOPICS=(
  rh.trip.lifecycle.events.v1
  rh.driver.location.pings.v1
  rh.rider.app.events.v1
  rh.payment.transactions.v1
  rh.pricing.surge.signals.v1
  rh.promotion.events.v1
  rh.refund.events.v1
  rh.review.events.v1
  rh.earnings.events.v1
  rh.fraud.signals.v1
  rh.support.tickets.v1
)

for topic in "${TOPICS[@]}"; do
  "$KAFKA_TOPICS_CMD" --bootstrap-server "$BOOTSTRAP_SERVER" \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions "$PARTITIONS" \
    --replication-factor "$REPLICATION"
done

echo "Kafka topic bootstrap completed."
