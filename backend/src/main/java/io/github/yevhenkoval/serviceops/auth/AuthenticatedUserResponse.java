package io.github.yevhenkoval.serviceops.auth;

public record AuthenticatedUserResponse(String username, UserRole role) {
}
