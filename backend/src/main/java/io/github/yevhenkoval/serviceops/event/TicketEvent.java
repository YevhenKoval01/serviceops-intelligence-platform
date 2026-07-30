package io.github.yevhenkoval.serviceops.event;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "ticket_events")
public class TicketEvent {

    @Id
    private UUID id;

    @Column(name = "ticket_id", nullable = false)
    private UUID ticketId;

    @Column(name = "event_type", nullable = false, length = 100)
    private String eventType;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "event_payload", nullable = false, columnDefinition = "jsonb")
    private JsonNode eventPayload;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected TicketEvent() {
    }

    public TicketEvent(UUID id, UUID ticketId, String eventType, JsonNode eventPayload, Instant createdAt) {
        this.id = id;
        this.ticketId = ticketId;
        this.eventType = eventType;
        this.eventPayload = eventPayload;
        this.createdAt = createdAt;
    }

    public UUID getId() {
        return id;
    }

    public UUID getTicketId() {
        return ticketId;
    }

    public String getEventType() {
        return eventType;
    }

    public JsonNode getEventPayload() {
        return eventPayload;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
