select *
from {{ ref('fct_ticket_performance') }}
where (resolution_sla_met is not null and resolved_at is null)
   or (first_response_sla_met is not null and first_response_at is null)
   or (is_open_backlog and status = 'RESOLVED')
   or (not is_open_backlog and status <> 'RESOLVED')
