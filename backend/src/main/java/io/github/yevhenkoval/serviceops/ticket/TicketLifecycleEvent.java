package io.github.yevhenkoval.serviceops.ticket;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "ticket_lifecycle_events")
public class TicketLifecycleEvent {

    @Id
    private UUID id;

    @Column(name = "ticket_id", nullable = false)
    private UUID ticketId;

    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false, length = 32)
    private TicketLifecycleEventType eventType;

    @Enumerated(EnumType.STRING)
    @Column(name = "previous_status", length = 32)
    private TicketStatus previousStatus;

    @Enumerated(EnumType.STRING)
    @Column(name = "current_status", nullable = false, length = 32)
    private TicketStatus currentStatus;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    protected TicketLifecycleEvent() {
    }

    public TicketLifecycleEvent(
            UUID id,
            UUID ticketId,
            TicketLifecycleEventType eventType,
            TicketStatus previousStatus,
            TicketStatus currentStatus,
            Instant occurredAt
    ) {
        this.id = id;
        this.ticketId = ticketId;
        this.eventType = eventType;
        this.previousStatus = previousStatus;
        this.currentStatus = currentStatus;
        this.occurredAt = occurredAt;
    }

    public UUID getId() {
        return id;
    }

    public UUID getTicketId() {
        return ticketId;
    }

    public TicketLifecycleEventType getEventType() {
        return eventType;
    }

    public TicketStatus getPreviousStatus() {
        return previousStatus;
    }

    public TicketStatus getCurrentStatus() {
        return currentStatus;
    }

    public Instant getOccurredAt() {
        return occurredAt;
    }
}
