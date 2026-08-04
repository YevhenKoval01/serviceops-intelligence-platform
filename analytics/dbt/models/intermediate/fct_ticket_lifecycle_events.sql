select
    lifecycle_event_id,
    ticket_id,
    row_number() over (
        partition by ticket_id
        order by occurred_at, lifecycle_event_id
    ) as event_sequence,
    event_type,
    previous_status,
    current_status,
    occurred_at,
    lag(current_status) over (
        partition by ticket_id
        order by occurred_at, lifecycle_event_id
    ) as prior_recorded_status,
    extract(
        epoch from occurred_at - lag(occurred_at) over (
            partition by ticket_id
            order by occurred_at, lifecycle_event_id
        )
    ) / 60.0 as minutes_since_previous_event
from {{ ref('stg_ticket_lifecycle_events') }}
