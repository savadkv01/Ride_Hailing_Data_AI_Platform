# Open Data Ingestion (NYC + Chicago)

## Sources decided in strategy
- NYC TLC Trip Records
- Chicago Taxi Trips

## Flow
1. Download raw files into Bronze Open landing.
2. Normalize each source into canonical `OP_TRIP_EVENTS` parquet.
3. Feed normalized outputs to Kafka/Spark ingestion in later stages.

## Commands

### NYC TLC download
```powershell
python ingestion/open_data/download_nyc_tlc.py --year 2024 --month 1 --output-dir lakehouse/bronze/open/nyc_tlc
```

### Chicago Taxi download (Socrata)
```powershell
python ingestion/open_data/download_chicago_taxi.py --limit 200000 --output-file lakehouse/bronze/open/chicago_taxi/chicago_taxi_trips.csv
```

### Normalize to canonical schema
```powershell
python ingestion/open_data/normalize_nyc_to_canonical.py --input lakehouse/bronze/open/nyc_tlc/yellow_tripdata_2024-01.parquet --output lakehouse/bronze/canonical/op_trip_events_nyc_2024_01.parquet
python ingestion/open_data/normalize_chicago_to_canonical.py --input lakehouse/bronze/open/chicago_taxi/chicago_taxi_trips.csv --output lakehouse/bronze/canonical/op_trip_events_chicago_sample.parquet
```

## Notes
- Canonical mapping logic follows `config/source_catalog/canonical_alignment.yaml`.
- Pseudonymous rider/driver IDs are generated for open data.

## New City Template Scaffolds

Use these templates when onboarding a new city source:

- `ingestion/open_data/download_city_template.py`
- `ingestion/open_data/normalize_city_to_canonical_template.py`

### Template download command
```powershell
python ingestion/open_data/download_city_template.py \
	--input-url "https://example-city.gov/api/trips.csv" \
	--output-file lakehouse/bronze/open/sf/sf_trips.csv
```

### Template normalize command
```powershell
python ingestion/open_data/normalize_city_to_canonical_template.py \
	--input lakehouse/bronze/open/sf/sf_trips.csv \
	--output lakehouse/bronze/canonical/op_trip_events_sf.parquet \
	--city-id SF \
	--source-system sf_open_data \
	--pickup-ts-col pickup_datetime \
	--dropoff-ts-col dropoff_datetime \
	--trip-id-col trip_id \
	--driver-id-col driver_id \
	--append \
	--filter-date today
```
