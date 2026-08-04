with bounds as (
    select
        coalesce(min(created_at)::date, current_date) as first_date,
        greatest(coalesce(max(created_at)::date, current_date), current_date) as last_date
    from {{ ref('stg_tickets') }}
)
select
    date_day::date as date_day,
    extract(isoyear from date_day)::integer as iso_year,
    extract(quarter from date_day)::integer as quarter_number,
    extract(month from date_day)::integer as month_number,
    to_char(date_day, 'Mon') as month_name,
    to_char(date_day, 'YYYY-MM') as year_month,
    extract(week from date_day)::integer as iso_week,
    extract(isodow from date_day)::integer as iso_weekday
from bounds
cross join lateral generate_series(first_date, last_date, interval '1 day') as date_day
