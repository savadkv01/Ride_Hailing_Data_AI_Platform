{{ config(unique_key='earning_fact_key') }}

select
    md5(coalesce(trip_id, event_id) || '_earn') as earning_fact_key,
    trip_id,
    md5(driver_id) as driver_key,
    md5(city_id) as city_key,
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    coalesce(driver_payout, 0) as base_earning,
    0::numeric as surge_bonus,
    0::numeric as incentive_bonus,
    0::numeric as tip_amount,
    0::numeric as adjustment_amount,
    coalesce(driver_payout, 0) as net_driver_earning,
    event_time as created_at
from {{ ref('stg_silver_canonical_events') }}
where driver_id is not null and trip_id is not null
{% if is_incremental() %}
  and event_time > (select coalesce(max(created_at), '1970-01-01') from {{ this }})
{% endif %}
