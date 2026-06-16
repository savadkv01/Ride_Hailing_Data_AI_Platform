select
    cast(event_time as date) as event_date,
    city_id,
    sum(case when event_type = 'trip_completed' then 1 else 0 end) as completed_trips,
    sum(case when event_type = 'trip_cancelled' then 1 else 0 end) as cancelled_trips,
    sum(coalesce(fare_total, 0)) as gross_fare_total,
    sum(coalesce(platform_fee, 0)) as platform_fee_total,
    sum(coalesce(driver_payout, 0)) as driver_payout_total,
    avg(coalesce(surge_multiplier, 1.0)) as avg_surge_multiplier
from {{ ref('stg_silver_canonical_events') }}
group by 1, 2
