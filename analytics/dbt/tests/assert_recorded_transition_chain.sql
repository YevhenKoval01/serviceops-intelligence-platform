select *
from {{ ref('fct_ticket_lifecycle_events') }}
where event_type in ('STATUS_CHANGED', 'REOPENED')
  and previous_status is distinct from prior_recorded_status
