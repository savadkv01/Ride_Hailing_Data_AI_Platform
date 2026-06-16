# Synthetic Source Ingestion Catalog

Each synthetic dataset has a separate metadata spec under:
- `config/source_catalog/synthetic/`

These specs define:
- Domain mapping
- Kafka topic
- Target operational table
- Generator script path
- Key fields and watermark column

## Domain coverage
- Trip events
- Driver location
- Rider app events
- Payments
- Surge pricing
- Promotions
- Refunds
- Reviews
- Driver earnings
- Incentives
- Fraud signals
- Support tickets
- Geo events
- City aggregations
- Revenue/margin

## Next implementation step
Stage 6 will implement producer scripts for each `generator_script` path and publish to the specified topics.

## Stage 6 producer runners (implemented)

### Install dependencies
```powershell
pip install -r ingestion/synthetic/requirements.txt
```

### Run one synthetic source producer
```powershell
python -m ingestion.synthetic.producer_runner --source-config config/source_catalog/synthetic/synthetic_trip_events.yaml --bootstrap-servers localhost:9094 --events-per-second 2 --max-events 100
```

### Run all synthetic source producers from catalog index
```powershell
python -m ingestion.synthetic.catalog_producer_manager --catalog-index config/source_catalog/source_catalog_index.yaml --bootstrap-servers localhost:9094 --events-per-second 1 --max-events 50
```

### Notes
- `--max-events 0` keeps producers running continuously.
- `localhost:9094` maps to Kafka external listener from docker compose.
- Producers read topic + generator metadata directly from source catalog YAML files.
