from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch producers for all synthetic sources from source catalog index.")
    parser.add_argument(
        "--catalog-index",
        default="config/source_catalog/source_catalog_index.yaml",
        help="Path to source catalog index yaml",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9094",
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--events-per-second",
        type=float,
        default=1.0,
        help="Events per second per producer",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="Stop each producer after N events (0 = run forever)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog_path = Path(args.catalog_index)
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog index not found: {catalog_path}")

    catalog = load_yaml(catalog_path)
    synthetic_sources: list[str] = catalog.get("synthetic_sources", [])
    if not synthetic_sources:
        raise ValueError("No synthetic_sources found in catalog index")

    processes: list[subprocess.Popen] = []
    try:
        for source_path in synthetic_sources:
            cmd = [
                sys.executable,
                "-m",
                "ingestion.synthetic.producer_runner",
                "--source-config",
                source_path,
                "--bootstrap-servers",
                args.bootstrap_servers,
                "--events-per-second",
                str(args.events_per_second),
                "--max-events",
                str(args.max_events),
            ]
            process = subprocess.Popen(cmd)
            processes.append(process)
            print(f"[manager] started producer for {source_path} pid={process.pid}")

        exit_codes = [process.wait() for process in processes]
        failed = [code for code in exit_codes if code != 0]
        if failed:
            raise RuntimeError(f"One or more producer processes failed: {exit_codes}")
    except KeyboardInterrupt:
        print("[manager] stopping producers...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()


if __name__ == "__main__":
    main()
