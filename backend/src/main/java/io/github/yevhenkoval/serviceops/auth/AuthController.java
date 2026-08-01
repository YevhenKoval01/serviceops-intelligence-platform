package io.github.yevhenkoval.serviceops.auth;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import jakarta.validation.Valid;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @Operation(summary = "Sign in", description = "Exchanges local credentials for a short-lived JWT.")
    @ApiResponse(responseCode = "200", description = "Credentials accepted")
    @ApiResponse(responseCode = "401", description = "Credentials rejected")
    @PostMapping("/login")
    LoginResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    @Operation(summary = "Get the authenticated user")
    @GetMapping("/me")
    AuthenticatedUserResponse currentUser(Authentication authentication) {
        return authService.currentUser(authentication);
    }
}
