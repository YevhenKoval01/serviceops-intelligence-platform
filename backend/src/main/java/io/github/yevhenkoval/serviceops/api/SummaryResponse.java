package io.github.yevhenkoval.serviceops.api;

public record SummaryResponse(long total, long open, long inProgress, long resolved) {
}
