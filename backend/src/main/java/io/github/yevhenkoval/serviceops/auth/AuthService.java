package io.github.yevhenkoval.serviceops.auth;

import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private static final String ROLE_PREFIX = "ROLE_";

    private final AuthenticationManager authenticationManager;
    private final TokenService tokenService;

    public AuthService(AuthenticationManager authenticationManager, TokenService tokenService) {
        this.authenticationManager = authenticationManager;
        this.tokenService = tokenService;
    }

    public LoginResponse login(LoginRequest request) {
        Authentication authentication = authenticationManager.authenticate(
                UsernamePasswordAuthenticationToken.unauthenticated(
                        request.username().trim(),
                        request.password()
                )
        );
        UserRole role = roleOf(authentication);
        IssuedToken token = tokenService.issue(authentication, role);
        return new LoginResponse(
                token.value(),
                "Bearer",
                token.expiresIn(),
                token.expiresAt(),
                new AuthenticatedUserResponse(authentication.getName(), role)
        );
    }

    public AuthenticatedUserResponse currentUser(Authentication authentication) {
        return new AuthenticatedUserResponse(authentication.getName(), roleOf(authentication));
    }

    private UserRole roleOf(Authentication authentication) {
        return authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .filter(authority -> authority.startsWith(ROLE_PREFIX))
                .map(authority -> UserRole.valueOf(authority.substring(ROLE_PREFIX.length())))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("Authenticated user has no supported role"));
    }
}
