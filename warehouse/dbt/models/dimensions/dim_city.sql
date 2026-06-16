select distinct
    md5(city_id) as city_key,
    city_id,
    city_id as city_name,
    'NA' as country_code,
    'UTC' as timezone,
    'default' as region_cluster,
    'standard' as regulatory_tier
from {{ ref('stg_silver_canonical_events') }}
where city_id is not null
