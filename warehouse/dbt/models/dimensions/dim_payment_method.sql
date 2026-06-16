select distinct
    md5(coalesce(source_system, 'unknown')) as payment_method_key,
    coalesce(source_system, 'unknown') as method_code,
    'mixed' as method_type,
    'platform' as provider,
    'standard' as risk_profile
from {{ ref('stg_silver_canonical_events') }}
