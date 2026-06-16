import argparse
from pathlib import Path
import hashlib
from datetime import datetime
import sys
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.contract_validator import validate_dataframe


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    trip_id = (
        "nyc_"
        + df["VendorID"].astype(str)
        + "_"
        + df["tpep_pickup_datetime"].astype(str)
        + "_"
        + df["PULocationID"].astype(str)
        + "_"
        + df["DOLocationID"].astype(str)
    )
    out = pd.DataFrame()
    out["event_id"] = trip_id.apply(lambda x: _hash_value(f"evt_{x}"))
    out["trip_id"] = trip_id
    out["rider_id"] = df.apply(
        lambda row: _hash_value(f"nyc_rider_{row['PULocationID']}_{row['DOLocationID']}_{row['tpep_pickup_datetime']}"), axis=1
    )
    out["driver_id"] = df["VendorID"].astype(str).apply(lambda x: _hash_value(f"nyc_driver_{x}"))
    out["city_id"] = "NYC"
    out["event_type"] = "trip_completed"
    out["event_time"] = df["tpep_dropoff_datetime"]
    out["pickup_ts"] = df["tpep_pickup_datetime"]
    out["dropoff_ts"] = df["tpep_dropoff_datetime"]
    out["pickup_lat"] = None
    out["pickup_lng"] = None
    out["dropoff_lat"] = None
    out["dropoff_lng"] = None
    out["distance_km"] = pd.to_numeric(df.get("trip_distance", 0), errors="coerce").fillna(0) * 1.60934
    out["duration_sec"] = (
        pd.to_datetime(df["tpep_dropoff_datetime"], errors="coerce")
        - pd.to_datetime(df["tpep_pickup_datetime"], errors="coerce")
    ).dt.total_seconds().fillna(0)
    out["ingestion_time"] = pd.Timestamp.utcnow()
    out["fare_total"] = df.get("total_amount", 0)
    out["surge_multiplier"] = 1.0
    out["promotion_amount"] = 0.0
    out["platform_fee"] = out["fare_total"] * 0.20
    out["driver_payout"] = out["fare_total"] - out["platform_fee"]
    out["payment_method_code"] = df.get("payment_type", "unknown").astype(str)
    out["source_system"] = "nyc_tlc"
    out["source_record_id"] = trip_id
    out["schema_version"] = "nyc_v1"
    return out


def parse_filter_date(value: str) -> datetime.date:
    normalized = value.strip().lower()
    if normalized == "today":
        return datetime.utcnow().date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def filter_by_date(df: pd.DataFrame, filter_date: datetime.date) -> pd.DataFrame:
    pickup_ts = pd.to_datetime(df["tpep_pickup_datetime"], errors="coerce", utc=True)
    return df.loc[pickup_ts.dt.date == filter_date].copy()


def write_output(df: pd.DataFrame, output_path: Path, append: bool) -> None:
    if append and output_path.exists():
        existing_df = pd.read_parquet(output_path)
        df = pd.concat([existing_df, df], ignore_index=True)
        df = df.drop_duplicates(subset=["event_id"], keep="last")
    df.to_parquet(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize NYC TLC raw files to canonical OP_TRIP_EVENTS schema.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--append", action="store_true", help="Incremental mode: append and deduplicate by event_id.")
    parser.add_argument(
        "--contract-file",
        default="config/contracts/op_trip_events_contract_v1.json",
        help="Path to contract JSON used for schema/quality validation.",
    )
    parser.add_argument(
        "--filter-date",
        type=parse_filter_date,
        help="Keep only one day of records by pickup timestamp (YYYY-MM-DD or 'today').",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.suffix.lower() == ".parquet":
        source_df = pd.read_parquet(input_path)
    else:
        source_df = pd.read_csv(input_path)

    if args.filter_date is not None:
        source_df = filter_by_date(source_df, args.filter_date)

    canonical_df = normalize(source_df)

    validation = validate_dataframe(canonical_df, contract_file=args.contract_file)
    if not validation["valid"]:
        raise ValueError(f"Contract validation failed: {validation['errors']}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(canonical_df, output_path, append=args.append)
    print(f"Canonical file written: {output_path}")


if __name__ == "__main__":
    main()
