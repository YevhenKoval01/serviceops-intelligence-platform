package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.Priority;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateTicketRequest(
        @Schema(example = "Production API unavailable")
        @NotBlank @Size(min = 5, max = 150) String title,
        @Schema(example = "Every customer API request returns a server error and order processing is blocked.")
        @NotBlank @Size(min = 10, max = 4000) String description,
        @Schema(example = "HIGH", nullable = true)
        Priority reportedPriority
) {
    public CreateTicketRequest {
        title = title == null ? null : title.trim();
        description = description == null ? null : description.trim();
    }
}
