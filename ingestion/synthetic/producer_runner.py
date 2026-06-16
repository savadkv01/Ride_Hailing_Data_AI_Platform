from __future__ import annotations

import argparse
import importlib
import json
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

import yaml
from kafka import KafkaProducer


RUNNING = True


def _handle_signal(signum: int, frame: Any) -> None:
    del signum, frame
    global RUNNING
    RUNNING = False


@dataclass
class SourceConfig:
    source_id: str
    kafka_topic: str
    generator_script: str


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def to_module_path(generator_script: str) -> str:
    normalized = generator_script.replace("\\", "/")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def load_source_config(source_config_path: Path) -> SourceConfig:
    config = load_yaml(source_config_path)
    return SourceConfig(
        source_id=config["source_id"],
        kafka_topic=config["kafka_topic"],
        generator_script=config["generator_script"],
    )


def load_generator(module_path: str) -> Callable[[], dict]:
    module = importlib.import_module(module_path)
    if not hasattr(module, "generate"):
        raise AttributeError(f"Module '{module_path}' must define a generate() function")
    generate_fn = getattr(module, "generate")
    if not callable(generate_fn):
        raise TypeError(f"generate in '{module_path}' is not callable")
    return generate_fn


def build_producer(bootstrap_servers: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        acks="all",
        linger_ms=50,
        retries=5,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def run_stream(
    source_config_path: Path,
    bootstrap_servers: str,
    events_per_second: float,
    max_events: int,
) -> int:
    source = load_source_config(source_config_path)
    module_path = to_module_path(source.generator_script)
    generate = load_generator(module_path)
    producer = build_producer(bootstrap_servers)

    interval = 1.0 / events_per_second if events_per_second > 0 else 0.0
    sent_count = 0

    print(
        f"[producer] source={source.source_id} topic={source.kafka_topic} "
        f"module={module_path} bootstrap={bootstrap_servers}"
    )

    while RUNNING:
        payload = generate()
        payload.setdefault("source_id", source.source_id)
        payload.setdefault("topic", source.kafka_topic)
        future = producer.send(source.kafka_topic, payload)
        future.get(timeout=30)
        sent_count += 1

        if max_events > 0 and sent_count >= max_events:
            break

        if interval > 0:
            time.sleep(interval)

    producer.flush(timeout=10)
    producer.close()
    print(f"[producer] source={source.source_id} sent={sent_count}")
    return sent_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run synthetic Kafka producer for one source config.")
    parser.add_argument(
        "--source-config",
        required=True,
        help="Path to synthetic source config yaml (e.g., config/source_catalog/synthetic/synthetic_trip_events.yaml)",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9094",
        help="Kafka bootstrap servers (default: localhost:9094)",
    )
    parser.add_argument(
        "--events-per-second",
        type=float,
        default=2.0,
        help="Emission rate per producer",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="Stop after N events (0 = run forever)",
    )
    return parser.parse_args()


def main() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    args = parse_args()
    source_config_path = Path(args.source_config)
    if not source_config_path.exists():
        raise FileNotFoundError(f"Source config not found: {source_config_path}")

    try:
        run_stream(
            source_config_path=source_config_path,
            bootstrap_servers=args.bootstrap_servers,
            events_per_second=args.events_per_second,
            max_events=args.max_events,
        )
    except Exception as exc:
        print(f"[producer] failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
