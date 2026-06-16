{{ config(unique_key='trip_fact_key') }}

select
    md5(coalesce(trip_id, event_id)) as trip_fact_key,
    trip_id,
    md5(rider_id) as rider_key,
    md5(driver_id) as driver_key,
    md5(vehicle_id) as vehicle_key,
    md5(city_id) as city_key,
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    md5(coalesce(cast(promotion_amount as varchar), '0')) as promotion_key,
    md5(coalesce(source_system, 'unknown')) as payment_method_key,
    coalesce(fare_total, 0) as final_fare,
    coalesce(surge_multiplier, 1.0) as surge_multiplier,
    coalesce(promotion_amount, 0) as promotion_amount,
    coalesce(platform_fee, 0) as platform_fee,
    coalesce(driver_payout, 0) as driver_payout,
    case when event_type = 'trip_completed' then 1 else 0 end as completed_flag,
    case when event_type = 'trip_cancelled' then 1 else 0 end as cancelled_flag,
    event_time as created_at
from {{ ref('stg_silver_canonical_events') }}
where trip_id is not null
{% if is_incremental() %}
  and event_time > (select coalesce(max(created_at), '1970-01-01') from {{ this }})
{% endif %}
