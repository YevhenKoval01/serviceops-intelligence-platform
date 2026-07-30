CREATE TABLE tickets (
    id UUID PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description VARCHAR(4000) NOT NULL,
    status VARCHAR(32) NOT NULL,
    reported_priority VARCHAR(16),
    predicted_priority VARCHAR(16),
    predicted_category VARCHAR(32),
    prediction_confidence NUMERIC(6, 5),
    model_version VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_ticket_status
        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    CONSTRAINT chk_reported_priority
        CHECK (reported_priority IS NULL OR reported_priority IN ('LOW', 'MEDIUM', 'HIGH')),
    CONSTRAINT chk_predicted_priority
        CHECK (predicted_priority IS NULL OR predicted_priority IN ('LOW', 'MEDIUM', 'HIGH')),
    CONSTRAINT chk_prediction_confidence
        CHECK (prediction_confidence IS NULL OR prediction_confidence BETWEEN 0 AND 1)
);

CREATE TABLE ticket_events (
    id UUID PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(id),
    event_type VARCHAR(100) NOT NULL,
    event_payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE processed_events (
    event_id UUID PRIMARY KEY,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX idx_ticket_events_ticket_id ON ticket_events(ticket_id);
