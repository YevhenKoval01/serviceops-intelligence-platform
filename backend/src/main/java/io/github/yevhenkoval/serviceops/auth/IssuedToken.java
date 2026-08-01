package io.github.yevhenkoval.serviceops.auth;

import java.time.Instant;

record IssuedToken(String value, Instant expiresAt, long expiresIn) {
}
