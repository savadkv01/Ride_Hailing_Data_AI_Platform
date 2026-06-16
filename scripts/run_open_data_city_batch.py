import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


def parse_for_date(value: str) -> datetime:
    normalized = value.strip().lower()
    if normalized == "today":
        return datetime.utcnow()
    return datetime.strptime(value, "%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run open-data download + normalization for one city.")
    parser.add_argument("--city-id", required=True, help="Supported: NYC, CHICAGO")
    parser.add_argument("--nyc-year", type=int, default=2024)
    parser.add_argument("--nyc-month", type=int, default=1)
    parser.add_argument("--chicago-limit", type=int, default=200000)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--for-date", type=parse_for_date)
    return parser.parse_args()


def run_step(command: list[str]) -> dict:
    started = time.perf_counter()
    completed = subprocess.run(command, check=False)
    duration = round(time.perf_counter() - started, 3)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}")
    return {
        "command": " ".join(command),
        "return_code": int(completed.returncode),
        "duration_seconds": duration,
    }


def run_nyc(args: argparse.Namespace, for_date_text: str | None) -> dict:
    nyc_year = args.nyc_year
    nyc_month = args.nyc_month
    if args.for_date is not None:
        nyc_year = args.for_date.year
        nyc_month = args.for_date.month

    nyc_raw = Path(f"lakehouse/bronze/open/nyc_tlc/yellow_tripdata_{nyc_year}-{nyc_month:02d}.parquet")
    nyc_canonical = Path(f"lakehouse/bronze/canonical/op_trip_events_nyc_{nyc_year}_{nyc_month:02d}.parquet")

    steps = [
        run_step(
            [
                "python",
                "ingestion/open_data/download_nyc_tlc.py",
                "--year",
                str(nyc_year),
                "--month",
                str(nyc_month),
                "--output-dir",
                "lakehouse/bronze/open/nyc_tlc",
            ]
        ),
        run_step(
            [
                "python",
                "ingestion/open_data/normalize_nyc_to_canonical.py",
                "--input",
                str(nyc_raw),
                "--output",
                str(nyc_canonical),
                *(["--append"] if args.incremental else []),
                *(["--filter-date", for_date_text] if for_date_text is not None else []),
            ]
        ),
    ]

    return {
        "city_id": "NYC",
        "for_date": for_date_text,
        "incremental": args.incremental,
        "raw": nyc_raw.as_posix(),
        "canonical": nyc_canonical.as_posix(),
        "steps": steps,
    }


def run_chicago(args: argparse.Namespace, for_date_text: str | None) -> dict:
    chicago_raw = Path("lakehouse/bronze/open/chicago_taxi/chicago_taxi_trips.csv")
    chicago_canonical = Path("lakehouse/bronze/canonical/op_trip_events_chicago_sample.parquet")

    download_command = [
        "python",
        "ingestion/open_data/download_chicago_taxi.py",
        "--limit",
        str(args.chicago_limit),
        "--output-file",
        str(chicago_raw),
    ]
    if for_date_text is not None:
        download_command.extend(["--for-date", for_date_text])

    normalize_command = [
        "python",
        "ingestion/open_data/normalize_chicago_to_canonical.py",
        "--input",
        str(chicago_raw),
        "--output",
        str(chicago_canonical),
        *(["--append"] if args.incremental else []),
        *(["--filter-date", for_date_text] if for_date_text is not None else []),
    ]

    steps = [run_step(download_command), run_step(normalize_command)]

    return {
        "city_id": "CHICAGO",
        "for_date": for_date_text,
        "incremental": args.incremental,
        "raw": chicago_raw.as_posix(),
        "canonical": chicago_canonical.as_posix(),
        "steps": steps,
    }


def main() -> None:
    args = parse_args()
    city_id = args.city_id.strip().upper()
    for_date_text = args.for_date.strftime("%Y-%m-%d") if args.for_date is not None else None

    if city_id == "NYC":
        summary = run_nyc(args, for_date_text)
    elif city_id == "CHICAGO":
        summary = run_chicago(args, for_date_text)
    else:
        raise SystemExit(f"Unsupported city-id: {args.city_id}. Supported: NYC, CHICAGO")

    print(json.dumps(summary))


if __name__ == "__main__":
    main()
