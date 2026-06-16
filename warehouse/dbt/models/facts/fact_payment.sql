{{ config(unique_key='payment_fact_key') }}

select
    md5(coalesce(payment_id, event_id)) as payment_fact_key,
    payment_id,
    trip_id,
    md5(rider_id) as rider_key,
    md5(city_id) as city_key,
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    md5(coalesce(source_system, 'unknown')) as payment_method_key,
    coalesce(payment_amount, 0) as captured_amount,
    coalesce(refund_amount, 0) as refunded_amount,
    0::numeric as chargeback_amount,
    0::numeric as fee_amount,
    event_time as created_at
from {{ ref('stg_silver_canonical_events') }}
where payment_id is not null
{% if is_incremental() %}
  and event_time > (select coalesce(max(created_at), '1970-01-01') from {{ this }})
{% endif %}
