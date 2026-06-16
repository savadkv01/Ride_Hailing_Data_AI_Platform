select distinct
    md5(vehicle_id) as vehicle_key,
    vehicle_id,
    'sedan' as vehicle_type,
    'unknown' as make,
    'unknown' as model,
    2024 as model_year,
    4 as capacity
from {{ ref('stg_silver_canonical_events') }}
where vehicle_id is not null
