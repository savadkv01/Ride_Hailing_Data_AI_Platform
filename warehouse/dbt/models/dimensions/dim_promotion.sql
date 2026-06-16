select distinct
    md5(coalesce(cast(promotion_amount as varchar), '0')) as promotion_key,
    'promo_' || coalesce(cast(promotion_amount as varchar), '0') as promotion_id,
    'dynamic' as campaign_type,
    'amount' as discount_type,
    coalesce(promotion_amount, 0) as cap_amount,
    min(event_time) over () as valid_from,
    null::timestamp as valid_to
from {{ ref('stg_silver_canonical_events') }}
