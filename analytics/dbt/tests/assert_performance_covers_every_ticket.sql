select
    ticket.ticket_id as source_ticket_id,
    performance.ticket_id as performance_ticket_id
from {{ ref('stg_tickets') }} as ticket
full outer join {{ ref('fct_ticket_performance') }} as performance
    on ticket.ticket_id = performance.ticket_id
where ticket.ticket_id is null
   or performance.ticket_id is null
