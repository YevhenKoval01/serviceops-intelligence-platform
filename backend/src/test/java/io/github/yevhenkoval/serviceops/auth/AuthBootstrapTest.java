package io.github.yevhenkoval.serviceops.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.password.PasswordEncoder;

class AuthBootstrapTest {

    @Test
    void createsMissingUsersWithEncodedPasswordsAndRoles() throws Exception {
        UserAccountRepository repository = mock(UserAccountRepository.class);
        PasswordEncoder passwordEncoder = mock(PasswordEncoder.class);
        when(repository.findByUsernameIgnoreCase(any())).thenReturn(Optional.empty());
        when(passwordEncoder.encode("operator_dev_2026")).thenReturn("operator-hash");
        when(passwordEncoder.encode("viewer_dev_2026")).thenReturn("viewer-hash");
        AuthProperties properties = new AuthProperties(
                "serviceops-local",
                "serviceops-api",
                Duration.ofMinutes(15),
                "local-development-signing-key-change-me-2026",
                new AuthProperties.Bootstrap(
                        true,
                        "operator",
                        "operator_dev_2026",
                        "viewer",
                        "viewer_dev_2026"
                )
        );
        AuthBootstrap bootstrap = new AuthBootstrap(
                repository,
                passwordEncoder,
                properties,
                Clock.fixed(Instant.parse("2026-08-01T10:00:00Z"), ZoneOffset.UTC)
        );

        bootstrap.run(null);

        ArgumentCaptor<UserAccount> accounts = ArgumentCaptor.forClass(UserAccount.class);
        verify(repository, org.mockito.Mockito.times(2)).save(accounts.capture());
        assertThat(accounts.getAllValues())
                .extracting(UserAccount::getUsername, UserAccount::getPasswordHash, UserAccount::getRole)
                .containsExactlyInAnyOrder(
                        org.assertj.core.groups.Tuple.tuple("operator", "operator-hash", UserRole.OPERATOR),
                        org.assertj.core.groups.Tuple.tuple("viewer", "viewer-hash", UserRole.VIEWER)
                );
    }
}
