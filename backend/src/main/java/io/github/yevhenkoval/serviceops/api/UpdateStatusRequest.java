package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.TicketStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

public record UpdateStatusRequest(
        @Schema(example = "IN_PROGRESS")
        @NotNull TicketStatus status
) {
}
