CREATE TABLE ticket_lifecycle_events (
    id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    event_type VARCHAR(32) NOT NULL,
    previous_status VARCHAR(32),
    current_status VARCHAR(32) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT chk_ticket_lifecycle_event_type
        CHECK (event_type IN ('CREATED', 'STATUS_CHANGED', 'REOPENED', 'MIGRATED')),
    CONSTRAINT chk_ticket_lifecycle_previous_status
        CHECK (previous_status IS NULL OR previous_status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    CONSTRAINT chk_ticket_lifecycle_current_status
        CHECK (current_status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    CONSTRAINT chk_ticket_lifecycle_transition
        CHECK (
            (event_type IN ('CREATED', 'MIGRATED') AND previous_status IS NULL)
            OR
            (event_type IN ('STATUS_CHANGED', 'REOPENED')
                AND previous_status IS NOT NULL
                AND previous_status <> current_status)
        ),
    CONSTRAINT chk_ticket_lifecycle_reopen
        CHECK (event_type <> 'REOPENED' OR previous_status = 'RESOLVED')
);

CREATE INDEX idx_ticket_lifecycle_events_ticket_time
    ON ticket_lifecycle_events(ticket_id, occurred_at, id);
CREATE INDEX idx_ticket_lifecycle_events_occurred_at
    ON ticket_lifecycle_events(occurred_at);

-- V1-V3 did not retain transitions. Preserve an explicit current-state snapshot for
-- existing rows rather than fabricating a status history that never existed.
INSERT INTO ticket_lifecycle_events (
    id,
    ticket_id,
    event_type,
    previous_status,
    current_status,
    occurred_at
)
SELECT
    id,
    id,
    'MIGRATED',
    NULL,
    status,
    updated_at
FROM tickets;
