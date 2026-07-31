package io.github.yevhenkoval.serviceops.api;

import io.swagger.v3.oas.annotations.media.Schema;

public record SummaryResponse(
        @Schema(example = "12") long total,
        @Schema(example = "7") long open,
        @Schema(example = "3") long inProgress,
        @Schema(example = "2") long resolved
) {
}
