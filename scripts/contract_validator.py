import json
from pathlib import Path

import pandas as pd


DEFAULT_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "config" / "contracts" / "op_trip_events_contract_v1.json"


def load_contract(contract_file: str | None = None) -> dict:
    contract_path = Path(contract_file) if contract_file else DEFAULT_CONTRACT_PATH
    with contract_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _check_required_columns(df: pd.DataFrame, required_fields: list[str], errors: list[str]) -> None:
    missing = [field for field in required_fields if field not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")


def _check_not_null(df: pd.DataFrame, not_null_fields: list[str], errors: list[str]) -> None:
    for field in not_null_fields:
        if field not in df.columns:
            continue
        null_count = int(df[field].isna().sum())
        if null_count > 0:
            errors.append(f"Column '{field}' has {null_count} null values")


def _check_non_negative(df: pd.DataFrame, columns: list[str], errors: list[str]) -> None:
    for column in columns:
        if column not in df.columns:
            continue
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        negative_count = int((numeric_series < 0).sum())
        if negative_count > 0:
            errors.append(f"Column '{column}' has {negative_count} negative values")


def _check_allowed_values(df: pd.DataFrame, column: str, allowed_values: list[str], errors: list[str]) -> None:
    if column not in df.columns:
        return
    actual_values = set(df[column].dropna().astype(str).unique().tolist())
    invalid_values = sorted(value for value in actual_values if value not in set(allowed_values))
    if invalid_values:
        errors.append(f"Column '{column}' has disallowed values: {invalid_values}")


def _check_primary_key_uniqueness(df: pd.DataFrame, primary_key: list[str], errors: list[str]) -> None:
    if not primary_key:
        return
    for column in primary_key:
        if column not in df.columns:
            return
    duplicate_count = int(df.duplicated(subset=primary_key, keep=False).sum())
    if duplicate_count > 0:
        errors.append(f"Primary key {primary_key} has {duplicate_count} duplicate rows")


def _check_field_types(df: pd.DataFrame, field_types: dict[str, str], errors: list[str]) -> None:
    for field, type_spec in field_types.items():
        if field not in df.columns:
            continue

        nullable = "|null" in type_spec
        base_type = type_spec.replace("|null", "")
        series = df[field]
        non_null = series.dropna()
        if non_null.empty:
            if nullable:
                continue
            continue

        if base_type == "float":
            coerced = pd.to_numeric(non_null, errors="coerce")
            invalid_count = int(coerced.isna().sum())
            if invalid_count > 0:
                errors.append(f"Column '{field}' has {invalid_count} non-float values")
        elif base_type == "integer":
            coerced = pd.to_numeric(non_null, errors="coerce", downcast="integer")
            invalid_count = int(coerced.isna().sum())
            if invalid_count > 0:
                errors.append(f"Column '{field}' has {invalid_count} non-integer values")
        elif base_type == "timestamp":
            coerced = pd.to_datetime(non_null, errors="coerce", utc=True)
            invalid_count = int(coerced.isna().sum())
            if invalid_count > 0:
                errors.append(f"Column '{field}' has {invalid_count} non-timestamp values")
        elif base_type == "string":
            invalid_count = int(non_null.apply(lambda value: isinstance(value, (dict, list, tuple, set))).sum())
            if invalid_count > 0:
                errors.append(f"Column '{field}' has {invalid_count} non-string-like values")


def validate_dataframe(df: pd.DataFrame, contract: dict | None = None, contract_file: str | None = None) -> dict:
    resolved_contract = contract or load_contract(contract_file)
    errors: list[str] = []

    required_fields = resolved_contract.get("required_fields", [])
    quality_rules = resolved_contract.get("quality_rules", {})
    field_types = resolved_contract.get("field_types", {})
    primary_key = resolved_contract.get("primary_key", [])

    _check_required_columns(df, required_fields, errors)
    _check_not_null(df, quality_rules.get("not_null", []), errors)
    _check_non_negative(df, quality_rules.get("non_negative", []), errors)

    if "allowed_event_type" in quality_rules:
        _check_allowed_values(df, "event_type", quality_rules["allowed_event_type"], errors)
    if "allowed_city_ids" in quality_rules:
        _check_allowed_values(df, "city_id", quality_rules["allowed_city_ids"], errors)

    _check_primary_key_uniqueness(df, primary_key, errors)
    _check_field_types(df, field_types, errors)

    return {
        "valid": len(errors) == 0,
        "row_count": int(len(df.index)),
        "error_count": len(errors),
        "errors": errors,
        "contract_name": resolved_contract.get("contract_name"),
        "contract_version": resolved_contract.get("version"),
    }


def validate_records(records: list[dict], contract: dict | None = None, contract_file: str | None = None) -> dict:
    return validate_dataframe(pd.DataFrame(records), contract=contract, contract_file=contract_file)
