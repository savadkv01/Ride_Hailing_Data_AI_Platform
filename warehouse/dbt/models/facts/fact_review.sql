{{ config(unique_key='review_fact_key') }}

select
    md5(coalesce(review_id, event_id)) as review_fact_key,
    review_id,
    trip_id,
    md5(rider_id) as rider_key,
    md5(driver_id) as driver_key,
    md5(city_id) as city_key,
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    coalesce(rating_value, 0) as rating_value,
    0::numeric as sentiment_score,
    event_time as created_at
from {{ ref('stg_silver_canonical_events') }}
where review_id is not null
{% if is_incremental() %}
  and event_time > (select coalesce(max(created_at), '1970-01-01') from {{ this }})
{% endif %}
