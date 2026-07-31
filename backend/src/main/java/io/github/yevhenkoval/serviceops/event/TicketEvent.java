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

    @Column(name = "published_at")
    private Instant publishedAt;

    @Column(name = "publish_attempts", nullable = false)
    private int publishAttempts;

    @Column(name = "next_attempt_at", nullable = false)
    private Instant nextAttemptAt;

    @Column(name = "last_publish_error", length = 1000)
    private String lastPublishError;

    protected TicketEvent() {
    }

    public TicketEvent(UUID id, UUID ticketId, String eventType, JsonNode eventPayload, Instant createdAt) {
        this.id = id;
        this.ticketId = ticketId;
        this.eventType = eventType;
        this.eventPayload = eventPayload;
        this.createdAt = createdAt;
        this.nextAttemptAt = createdAt;
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

    public Instant getPublishedAt() {
        return publishedAt;
    }

    public int getPublishAttempts() {
        return publishAttempts;
    }

    public Instant getNextAttemptAt() {
        return nextAttemptAt;
    }

    public String getLastPublishError() {
        return lastPublishError;
    }

    public boolean isPublished() {
        return publishedAt != null;
    }

    public void markPublished(Instant publishedAt) {
        this.publishedAt = publishedAt;
        this.publishAttempts += 1;
        this.lastPublishError = null;
    }

    public void markPublicationFailed(Instant nextAttemptAt, String error) {
        this.publishAttempts += 1;
        this.nextAttemptAt = nextAttemptAt;
        this.lastPublishError = truncate(error);
    }

    private String truncate(String value) {
        if (value == null || value.isBlank()) {
            return "Unknown publication failure";
        }
        return value.length() <= 1000 ? value : value.substring(0, 1000);
    }
}
