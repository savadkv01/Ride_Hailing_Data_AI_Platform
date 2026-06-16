select distinct
    md5(rider_id) as rider_key,
    rider_id,
    cast(min(event_date) over (partition by rider_id) as date) as signup_date,
    'standard' as rider_segment,
    md5(city_id) as city_key,
    'active' as lifecycle_status,
    current_timestamp as effective_from,
    null::timestamp as effective_to,
    true as is_current
from {{ ref('stg_silver_canonical_events') }}
where rider_id is not null
