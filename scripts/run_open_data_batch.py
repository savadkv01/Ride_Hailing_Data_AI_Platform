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
    parser = argparse.ArgumentParser(description="Run NYC + Chicago open-data download and normalization batch.")
    parser.add_argument("--nyc-year", type=int, default=2024)
    parser.add_argument("--nyc-month", type=int, default=1)
    parser.add_argument("--chicago-limit", type=int, default=200000)
    parser.add_argument("--incremental", action="store_true", help="Append normalized outputs and deduplicate by event_id.")
    parser.add_argument(
        "--for-date",
        type=parse_for_date,
        help="Daily mode. Use YYYY-MM-DD or 'today'. Chicago is filtered to this date; NYC uses this date's month.",
    )
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


def main() -> None:
    args = parse_args()

    nyc_year = args.nyc_year
    nyc_month = args.nyc_month
    chicago_for_date = None

    if args.for_date is not None:
        nyc_year = args.for_date.year
        nyc_month = args.for_date.month
        chicago_for_date = args.for_date.strftime("%Y-%m-%d")

    nyc_raw = Path(f"lakehouse/bronze/open/nyc_tlc/yellow_tripdata_{nyc_year}-{nyc_month:02d}.parquet")
    chicago_raw = Path("lakehouse/bronze/open/chicago_taxi/chicago_taxi_trips.csv")
    nyc_canonical = Path(f"lakehouse/bronze/canonical/op_trip_events_nyc_{nyc_year}_{nyc_month:02d}.parquet")
    chicago_canonical = Path("lakehouse/bronze/canonical/op_trip_events_chicago_sample.parquet")

    steps = []

    steps.append(
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
        )
    )

    chicago_command = [
        "python",
        "ingestion/open_data/download_chicago_taxi.py",
        "--limit",
        str(args.chicago_limit),
        "--output-file",
        str(chicago_raw),
    ]
    if chicago_for_date is not None:
        chicago_command.extend(["--for-date", chicago_for_date])
    steps.append(run_step(chicago_command))

    steps.append(
        run_step(
            [
                "python",
                "ingestion/open_data/normalize_nyc_to_canonical.py",
                "--input",
                str(nyc_raw),
                "--output",
                str(nyc_canonical),
                *(["--append"] if args.incremental else []),
                *(["--filter-date", chicago_for_date] if chicago_for_date is not None else []),
            ]
        )
    )

    steps.append(
        run_step(
            [
                "python",
                "ingestion/open_data/normalize_chicago_to_canonical.py",
                "--input",
                str(chicago_raw),
                "--output",
                str(chicago_canonical),
                *(["--append"] if args.incremental else []),
                *(["--filter-date", chicago_for_date] if chicago_for_date is not None else []),
            ]
        )
    )

    summary = {
        "incremental": args.incremental,
        "for_date": chicago_for_date,
        "nyc_raw": nyc_raw.as_posix(),
        "chicago_raw": chicago_raw.as_posix(),
        "nyc_canonical": nyc_canonical.as_posix(),
        "chicago_canonical": chicago_canonical.as_posix(),
        "steps": steps,
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
