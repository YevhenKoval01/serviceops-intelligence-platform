package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.TicketStatus;
import jakarta.validation.constraints.NotNull;

public record UpdateStatusRequest(@NotNull TicketStatus status) {
}
