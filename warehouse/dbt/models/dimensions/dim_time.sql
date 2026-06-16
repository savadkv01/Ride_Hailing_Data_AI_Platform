select distinct
    cast(to_char(event_time, 'YYYYMMDDHH24') as bigint) as time_key,
    cast(event_time as date) as full_date,
    extract(hour from event_time)::int as hour_of_day,
    extract(dow from event_time)::int as day_of_week,
    extract(week from event_time)::int as week_of_year,
    extract(month from event_time)::int as month_of_year,
    extract(quarter from event_time)::int as quarter_of_year,
    extract(year from event_time)::int as year_number,
    false as is_holiday
from {{ ref('stg_silver_canonical_events') }}
where event_time is not null
