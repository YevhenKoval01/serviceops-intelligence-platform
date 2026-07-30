package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.Priority;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateTicketRequest(
        @NotBlank @Size(min = 5, max = 150) String title,
        @NotBlank @Size(min = 10, max = 4000) String description,
        Priority reportedPriority
) {
}
