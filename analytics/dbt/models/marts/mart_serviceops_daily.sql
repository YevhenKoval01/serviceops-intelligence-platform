select
    md5(concat_ws('|', created_date::text, category, effective_priority)) as daily_slice_id,
    created_date,
    category,
    effective_priority,
    count(*) as tickets_created,
    count(*) filter (where status = 'RESOLVED') as tickets_resolved,
    count(*) filter (where is_open_backlog) as open_backlog,
    count(*) filter (where is_breached_backlog) as breached_backlog,
    count(*) filter (where resolution_sla_met) as resolution_sla_compliant,
    count(resolution_sla_met) as resolution_sla_evaluated,
    avg(first_response_minutes) as average_first_response_minutes,
    avg(resolution_minutes) as average_resolution_minutes,
    count(*) filter (where was_reopened) as reopened_tickets
from {{ ref('fct_ticket_performance') }}
group by created_date, category, effective_priority
