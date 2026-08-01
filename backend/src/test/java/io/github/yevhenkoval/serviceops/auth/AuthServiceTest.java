package io.github.yevhenkoval.serviceops.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;

class AuthServiceTest {

    @Test
    void authenticatesAndReturnsRoleBoundToken() {
        AuthenticationManager authenticationManager = mock(AuthenticationManager.class);
        TokenService tokenService = mock(TokenService.class);
        var authentication = UsernamePasswordAuthenticationToken.authenticated(
                "operator",
                null,
                org.springframework.security.core.authority.AuthorityUtils.createAuthorityList("ROLE_OPERATOR")
        );
        when(authenticationManager.authenticate(any())).thenReturn(authentication);
        when(tokenService.issue(authentication, UserRole.OPERATOR)).thenReturn(new IssuedToken(
                "signed-token",
                Instant.parse("2026-08-01T10:15:00Z"),
                900
        ));
        AuthService service = new AuthService(authenticationManager, tokenService);

        LoginResponse response = service.login(new LoginRequest(" operator ", "valid-password"));

        assertThat(response.accessToken()).isEqualTo("signed-token");
        assertThat(response.tokenType()).isEqualTo("Bearer");
        assertThat(response.expiresIn()).isEqualTo(900);
        assertThat(response.user()).isEqualTo(
                new AuthenticatedUserResponse("operator", UserRole.OPERATOR)
        );
    }
}
