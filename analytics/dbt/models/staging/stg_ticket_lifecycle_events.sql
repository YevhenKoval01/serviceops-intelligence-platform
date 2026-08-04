select
    id as lifecycle_event_id,
    ticket_id,
    event_type,
    previous_status,
    current_status,
    occurred_at
from {{ source('serviceops', 'ticket_lifecycle_events') }}
