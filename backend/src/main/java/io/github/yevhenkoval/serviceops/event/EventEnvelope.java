package io.github.yevhenkoval.serviceops.event;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.UUID;

public record EventEnvelope(
        UUID eventId,
        String eventType,
        int eventVersion,
        Instant occurredAt,
        UUID correlationId,
        UUID ticketId,
        JsonNode payload
) {
}
