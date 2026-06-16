import argparse
from datetime import datetime
from pathlib import Path
import hashlib
import pandas as pd


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_filter_date(value: str) -> datetime.date:
    normalized = value.strip().lower()
    if normalized == "today":
        return datetime.utcnow().date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def normalize(
    df: pd.DataFrame,
    city_id: str,
    source_system: str,
    pickup_ts_col: str,
    dropoff_ts_col: str,
    trip_id_col: str,
    driver_id_col: str,
) -> pd.DataFrame:
    trip_id = city_id.lower() + "_" + df[trip_id_col].astype(str)

    out = pd.DataFrame()
    out["event_id"] = trip_id.apply(lambda value: _hash_value(f"evt_{value}"))
    out["trip_id"] = trip_id
    out["rider_id"] = trip_id.apply(lambda value: _hash_value(f"rider_{value}"))
    out["driver_id"] = df[driver_id_col].astype(str).apply(lambda value: _hash_value(f"driver_{city_id}_{value}"))
    out["city_id"] = city_id.upper()
    out["event_type"] = "trip_completed"
    out["event_time"] = df[dropoff_ts_col]
    out["pickup_ts"] = df[pickup_ts_col]
    out["dropoff_ts"] = df[dropoff_ts_col]
    out["pickup_lat"] = pd.to_numeric(df.get("pickup_lat", None), errors="coerce")
    out["pickup_lng"] = pd.to_numeric(df.get("pickup_lng", None), errors="coerce")
    out["dropoff_lat"] = pd.to_numeric(df.get("dropoff_lat", None), errors="coerce")
    out["dropoff_lng"] = pd.to_numeric(df.get("dropoff_lng", None), errors="coerce")
    out["distance_km"] = pd.to_numeric(df.get("distance_km", 0), errors="coerce").fillna(0)
    out["duration_sec"] = pd.to_numeric(df.get("duration_sec", 0), errors="coerce").fillna(0)
    out["ingestion_time"] = pd.Timestamp.utcnow()
    out["fare_total"] = pd.to_numeric(df.get("fare_total", 0), errors="coerce").fillna(0)
    out["surge_multiplier"] = pd.to_numeric(df.get("surge_multiplier", 1.0), errors="coerce").fillna(1.0)
    out["promotion_amount"] = pd.to_numeric(df.get("promotion_amount", 0), errors="coerce").fillna(0)
    out["platform_fee"] = out["fare_total"] * 0.20
    out["driver_payout"] = out["fare_total"] - out["platform_fee"]
    out["payment_method_code"] = df.get("payment_method_code", "unknown").astype(str)
    out["source_system"] = source_system
    out["source_record_id"] = df[trip_id_col].astype(str)
    out["schema_version"] = "city_template_v1"
    return out


def filter_by_date(df: pd.DataFrame, pickup_ts_col: str, filter_date: datetime.date) -> pd.DataFrame:
    pickup_ts = pd.to_datetime(df[pickup_ts_col], errors="coerce", utc=True)
    return df.loc[pickup_ts.dt.date == filter_date].copy()


def write_output(df: pd.DataFrame, output_path: Path, append: bool) -> None:
    if append and output_path.exists():
        existing_df = pd.read_parquet(output_path)
        df = pd.concat([existing_df, df], ignore_index=True)
        df = df.drop_duplicates(subset=["event_id"], keep="last")
    df.to_parquet(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Template normalizer for onboarding a new city to canonical OP_TRIP_EVENTS.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--city-id", required=True)
    parser.add_argument("--source-system", required=True)
    parser.add_argument("--pickup-ts-col", default="pickup_ts")
    parser.add_argument("--dropoff-ts-col", default="dropoff_ts")
    parser.add_argument("--trip-id-col", default="trip_id")
    parser.add_argument("--driver-id-col", default="driver_id")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--filter-date", type=parse_filter_date)
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.suffix.lower() == ".parquet":
        source_df = pd.read_parquet(input_path)
    else:
        source_df = pd.read_csv(input_path)

    if args.filter_date is not None:
        source_df = filter_by_date(source_df, args.pickup_ts_col, args.filter_date)

    canonical_df = normalize(
        df=source_df,
        city_id=args.city_id,
        source_system=args.source_system,
        pickup_ts_col=args.pickup_ts_col,
        dropoff_ts_col=args.dropoff_ts_col,
        trip_id_col=args.trip_id_col,
        driver_id_col=args.driver_id_col,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(canonical_df, output_path, append=args.append)
    print(f"Canonical file written: {output_path}")


if __name__ == "__main__":
    main()
