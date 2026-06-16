{{ config(unique_key='operational_event_fact_key') }}

select
    md5(event_id) as operational_event_fact_key,
    event_id,
    trip_id,
    md5(rider_id) as rider_key,
    md5(driver_id) as driver_key,
    md5(city_id) as city_key,
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    event_type,
    1 as event_count,
    0::int as latency_ms,
    source_system,
    event_time as created_at
from {{ ref('stg_silver_canonical_events') }}
where event_id is not null
{% if is_incremental() %}
  and event_time > (select coalesce(max(created_at), '1970-01-01') from {{ this }})
{% endif %}
