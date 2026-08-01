package io.github.yevhenkoval.serviceops.auth;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("serviceops.auth")
public record AuthProperties(
        String issuer,
        String audience,
        Duration tokenTtl,
        String jwtSecret,
        Bootstrap bootstrap
) {

    private static final int MINIMUM_HMAC_KEY_BYTES = 32;

    public AuthProperties {
        if (issuer == null || issuer.isBlank()) {
            throw new IllegalArgumentException("serviceops.auth.issuer must not be blank");
        }
        if (audience == null || audience.isBlank()) {
            throw new IllegalArgumentException("serviceops.auth.audience must not be blank");
        }
        if (tokenTtl == null || tokenTtl.isNegative() || tokenTtl.isZero()) {
            throw new IllegalArgumentException("serviceops.auth.token-ttl must be positive");
        }
        if (jwtSecret == null
                || jwtSecret.getBytes(StandardCharsets.UTF_8).length < MINIMUM_HMAC_KEY_BYTES) {
            throw new IllegalArgumentException(
                    "serviceops.auth.jwt-secret must contain at least 32 UTF-8 bytes"
            );
        }
    }

    public record Bootstrap(
            boolean enabled,
            String operatorUsername,
            String operatorPassword,
            String viewerUsername,
            String viewerPassword
    ) {
    }
}
