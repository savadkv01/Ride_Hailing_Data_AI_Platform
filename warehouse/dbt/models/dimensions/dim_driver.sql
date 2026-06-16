select distinct
    md5(driver_id) as driver_key,
    driver_id,
    cast(min(event_date) over (partition by driver_id) as date) as onboarding_date,
    'standard' as driver_tier,
    md5(city_id) as city_key,
    'active' as lifecycle_status,
    'unrated' as rating_band,
    current_timestamp as effective_from,
    null::timestamp as effective_to,
    true as is_current
from {{ ref('stg_silver_canonical_events') }}
where driver_id is not null
