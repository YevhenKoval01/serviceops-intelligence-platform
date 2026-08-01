package io.github.yevhenkoval.serviceops.auth;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.github.yevhenkoval.serviceops.config.SecurityConfiguration;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(AuthController.class)
@Import(SecurityConfiguration.class)
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AuthService authService;

    @MockitoBean
    private DatabaseUserDetailsService userDetailsService;

    @Test
    void allowsAnonymousLogin() throws Exception {
        when(authService.login(any())).thenReturn(new LoginResponse(
                "signed-token",
                "Bearer",
                900,
                Instant.parse("2026-08-01T10:15:00Z"),
                new AuthenticatedUserResponse("operator", UserRole.OPERATOR)
        ));

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"operator","password":"operator_dev_2026"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").value("signed-token"))
                .andExpect(jsonPath("$.expiresIn").value(900))
                .andExpect(jsonPath("$.user.role").value("OPERATOR"));
    }

    @Test
    void returnsGenericProblemForInvalidCredentials() throws Exception {
        when(authService.login(any())).thenThrow(new BadCredentialsException("rejected"));

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"operator","password":"incorrect-password"}
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.title").value("Sign-in failed"))
                .andExpect(jsonPath("$.detail").value("The username or password is incorrect"));
    }

    @Test
    @WithMockUser(username = "viewer", roles = "VIEWER")
    void returnsCurrentAuthenticatedUser() throws Exception {
        when(authService.currentUser(any())).thenReturn(
                new AuthenticatedUserResponse("viewer", UserRole.VIEWER)
        );

        mockMvc.perform(get("/api/auth/me"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("viewer"))
                .andExpect(jsonPath("$.role").value("VIEWER"));
    }
}
