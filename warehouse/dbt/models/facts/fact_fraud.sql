{{ config(unique_key='fraud_fact_key') }}

select
    md5(coalesce(fraud_case_id, event_id)) as fraud_fact_key,
    fraud_case_id,
    trip_id,
    md5(rider_id) as rider_key,
    md5(driver_id) as driver_key,
    md5(city_id) as city_key,
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    coalesce(fraud_score, 0) as fraud_score,
    case when coalesce(fraud_score, 0) >= 0.8 then 'high' when coalesce(fraud_score, 0) >= 0.5 then 'medium' else 'low' end as risk_band,
    case when coalesce(fraud_score, 0) >= 0.8 then true else false end as blocked_flag,
    event_time as created_at
from {{ ref('stg_silver_canonical_events') }}
where fraud_case_id is not null
{% if is_incremental() %}
  and event_time > (select coalesce(max(created_at), '1970-01-01') from {{ this }})
{% endif %}
