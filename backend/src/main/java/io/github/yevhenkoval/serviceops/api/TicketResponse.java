package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.Priority;
import io.github.yevhenkoval.serviceops.ticket.Ticket;
import io.github.yevhenkoval.serviceops.ticket.TicketStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record TicketResponse(
        @Schema(example = "23dc7d80-d74f-4d56-8c8c-caf97dc9ed23")
        UUID id,
        @Schema(example = "Production API unavailable")
        String title,
        @Schema(example = "Every customer API request returns a server error and order processing is blocked.")
        String description,
        @Schema(example = "OPEN")
        TicketStatus status,
        @Schema(example = "HIGH", nullable = true)
        Priority reportedPriority,
        @Schema(example = "HIGH", nullable = true)
        Priority predictedPriority,
        @Schema(example = "TECHNICAL", nullable = true)
        String predictedCategory,
        @Schema(example = "0.87542", minimum = "0", maximum = "1", nullable = true)
        BigDecimal predictionConfidence,
        @Schema(example = "baseline-1", nullable = true)
        String modelVersion,
        @Schema(example = "2026-07-30T10:00:00Z")
        Instant createdAt,
        @Schema(example = "2026-07-30T10:00:02Z")
        Instant updatedAt,
        @Schema(example = "1")
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
