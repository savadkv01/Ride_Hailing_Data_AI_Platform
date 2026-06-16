from pathlib import Path
import argparse
import requests
from datetime import date, datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://data.cityofchicago.org/resource/wrvz-psew.csv"


def parse_date(value: str) -> date:
    normalized = value.strip().lower()
    if normalized == "today":
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _build_session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "ride-hailing-data-platform/1.0"})
    return session


def download_rows(limit: int, output_file: Path, for_date: date | None = None) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    params = {"$limit": limit}
    if for_date is not None:
        start = datetime.combine(for_date, datetime.min.time()).isoformat()
        end = datetime.combine(for_date + timedelta(days=1), datetime.min.time()).isoformat()
        params["$where"] = f"trip_start_timestamp >= '{start}' AND trip_start_timestamp < '{end}'"
        params["$order"] = "trip_start_timestamp ASC"
    session = _build_session()
    response = session.get(BASE_URL, params=params, timeout=180)
    response.raise_for_status()
    output_file.write_bytes(response.content)
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Chicago taxi trips sample via Socrata API.")
    parser.add_argument("--limit", type=int, default=200000)
    parser.add_argument("--output-file", default="lakehouse/bronze/open/chicago_taxi/chicago_taxi_trips.csv")
    parser.add_argument(
        "--for-date",
        type=parse_date,
        help="Filter rows for one calendar day (YYYY-MM-DD or 'today') using trip_start_timestamp.",
    )
    args = parser.parse_args()
    path = download_rows(args.limit, Path(args.output_file), args.for_date)
    print(f"Downloaded: {path}")


if __name__ == "__main__":
    main()
