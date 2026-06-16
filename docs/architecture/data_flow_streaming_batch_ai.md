# Ride-Hailing Data Flow (Streaming + Batch + Transformations + AI)

```mermaid
flowchart LR

  subgraph S1[Streaming Ingestion]
    SP[Synthetic Producers\nCatalog Producer Manager] --> K[(Kafka Topics)]
    K --> SB[Stage 7 Spark Bronze\nKafka To Bronze Parquet]
    SB --> SS[Stage 7 Spark Silver\nCanonical And Quarantine]
    SS --> SL[Silver To Postgres Loader\nLoad Spark Silver To Postgres]
    SL --> ST[(staging.silver_canonical_events)]
    SS --> SG[Stage 7 Spark Gold\nCity Hourly Metrics]
    K -. optional fallback .-> LK[Kafka To Postgres Direct Loader]
    LK -. optional fallback .-> ST
  end

  subgraph S2[Batch Ingestion - Open Data]
    NYC[NYC TLC Download\nDownload NYC TLC] --> BN[Normalize NYC\nNormalize NYC To Canonical]
    CHI[Chicago Download\nDownload Chicago Taxi] --> BC[Normalize Chicago\nNormalize Chicago To Canonical]
    BN --> BR[(lakehouse bronze canonical)]
    BC --> BR
  end

  subgraph S3[Warehouse Transformations]
    ST --> DBT[dbt Transform and Tests\nRun dbt With Audit]
    BR --> DBT
    DBT --> G[(gold schema\nDimensions Facts Marts)]
    G --> KPI[(gold.mart_city_daily_kpis)]
  end

  subgraph S4[AI Layer]
    G --> MF[ML Feature Builder\nBuild Feature Tables]
    MF --> MLT[(ml feature tables)]
    MLT --> MT[Model Training\nDemand Surge Fraud Churn]
    MT --> MA[(ml artifacts joblib)]

    G --> VC[Vector Builder\nBuild And Index Vectors]
    VC --> WV[(Weaviate\nRideDocument)]
    WV --> RAG[RAG Assistant\nRide Intelligence Assistant]
    RAG --> API[FastAPI Endpoints]
  end

  subgraph S5[Orchestration & Observability]
    AF[Airflow DAGs\nE2E and operational controls] --> SP
    AF --> SB
    AF --> SS
    AF --> SG
    AF --> NYC
    AF --> CHI
    AF --> DBT
    AF --> MF
    AF --> VC
    AF --> RAG

    AQ[(metadata.pipeline_run_audit)]
    DQ[Data Quality Monitor\nMonitor Data Quality] --> AQ
    LK --> AQ
    SL --> AQ
    SB --> AQ
    SS --> AQ
    SG --> AQ
    DBT --> AQ
    MF --> AQ
    MT --> AQ
    VC --> AQ
    RAG --> AQ
  end
```

## Notes
- Streaming lane and batch lane both converge into warehouse transformations before AI consumption.
- Spark Stage 7 runs in Airflow trigger-once mode for finite orchestration and feeds `staging.silver_canonical_events` via Spark Silver loader when enabled.
- Current resilient default for e2e is direct loader path (`run_stage7_spark_once=false`, `run_direct_kafka_loader=true`) to guarantee deterministic orchestration while Spark package/runtime hardening continues.
- Spark runtime now uses explicit submit path and connector settings (`spark-sql-kafka-0-10_2.12:3.5.1`, `spark.jars.ivy=/tmp/.ivy2`).
- Vector and RAG tasks resolve service URLs from environment (`WEAVIATE_URL`, `OLLAMA_URL`) for Docker network correctness.
- Stage 14 introduces multi-city scaling policy with city/date partitioning, capacity tiers, and configuration-driven city onboarding (`config/scaling/multi_city_expansion.yaml`).
- Airflow controls selective stage execution (ingestion-only, AI-only, DQ-only, full e2e).
- Centralized run auditing captures status, timing, and task context in `metadata.pipeline_run_audit`.
