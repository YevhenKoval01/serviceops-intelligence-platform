select *
from {{ ref('fct_ticket_performance') }}
where first_response_minutes < 0
   or resolution_minutes < 0
   or backlog_age_minutes < 0
