ALTER TABLE ticket_events
    ADD COLUMN published_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN publish_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN last_publish_error VARCHAR(1000),
    ADD CONSTRAINT chk_ticket_events_publish_attempts CHECK (publish_attempts >= 0);

CREATE INDEX idx_ticket_events_pending_publication
    ON ticket_events(next_attempt_at, created_at)
    WHERE published_at IS NULL;
