from pathlib import Path
import argparse
import requests

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def download_month(year: int, month: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"yellow_tripdata_{year}-{month:02d}.parquet"
    target = output_dir / file_name

    lookback_year = year
    lookback_month = month
    max_lookback_months = 24

    for _ in range(max_lookback_months):
        candidate_name = f"yellow_tripdata_{lookback_year}-{lookback_month:02d}.parquet"
        url = f"{BASE_URL}/{candidate_name}"
        response = requests.get(url, timeout=120)

        if response.status_code < 400:
            target.write_bytes(response.content)
            if candidate_name != file_name:
                print(
                    f"Requested {file_name} unavailable; used {candidate_name} as fallback and saved to {target}."
                )
            return target

        if response.status_code not in {403, 404}:
            response.raise_for_status()

        lookback_month -= 1
        if lookback_month == 0:
            lookback_month = 12
            lookback_year -= 1

    raise RuntimeError(
        f"NYC TLC parquet unavailable for requested {year}-{month:02d} and last {max_lookback_months} months."
    )

    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NYC TLC trip parquet files.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--output-dir", default="lakehouse/bronze/open/nyc_tlc")
    args = parser.parse_args()
    path = download_month(args.year, args.month, Path(args.output_dir))
    print(f"Downloaded: {path}")


if __name__ == "__main__":
    main()
