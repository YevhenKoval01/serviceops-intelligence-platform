package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.Priority;
import io.github.yevhenkoval.serviceops.ticket.Ticket;
import io.github.yevhenkoval.serviceops.ticket.TicketStatus;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record TicketResponse(
        UUID id,
        String title,
        String description,
        TicketStatus status,
        Priority reportedPriority,
        Priority predictedPriority,
        String predictedCategory,
        BigDecimal predictionConfidence,
        String modelVersion,
        Instant createdAt,
        Instant updatedAt,
        long version
) {
    public static TicketResponse from(Ticket ticket) {
        return new TicketResponse(
                ticket.getId(),
                ticket.getTitle(),
                ticket.getDescription(),
                ticket.getStatus(),
                ticket.getReportedPriority(),
                ticket.getPredictedPriority(),
                ticket.getPredictedCategory(),
                ticket.getPredictionConfidence(),
                ticket.getModelVersion(),
                ticket.getCreatedAt(),
                ticket.getUpdatedAt(),
                ticket.getVersion()
        );
    }
}
