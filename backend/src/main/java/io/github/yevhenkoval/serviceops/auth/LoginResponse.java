package io.github.yevhenkoval.serviceops.auth;

import java.time.Instant;

public record LoginResponse(
        String accessToken,
        String tokenType,
        long expiresIn,
        Instant expiresAt,
        AuthenticatedUserResponse user
) {
}
