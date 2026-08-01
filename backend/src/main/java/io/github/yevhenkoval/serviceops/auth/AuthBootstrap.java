package io.github.yevhenkoval.serviceops.auth;

import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(
        name = "serviceops.auth.bootstrap.enabled",
        havingValue = "true",
        matchIfMissing = true
)
public class AuthBootstrap implements ApplicationRunner {

    private static final int MINIMUM_PASSWORD_LENGTH = 12;

    private final UserAccountRepository userAccountRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthProperties properties;
    private final Clock clock;

    @Autowired
    public AuthBootstrap(
            UserAccountRepository userAccountRepository,
            PasswordEncoder passwordEncoder,
            AuthProperties properties
    ) {
        this(userAccountRepository, passwordEncoder, properties, Clock.systemUTC());
    }

    AuthBootstrap(
            UserAccountRepository userAccountRepository,
            PasswordEncoder passwordEncoder,
            AuthProperties properties,
            Clock clock
    ) {
        this.userAccountRepository = userAccountRepository;
        this.passwordEncoder = passwordEncoder;
        this.properties = properties;
        this.clock = clock;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments arguments) {
        AuthProperties.Bootstrap bootstrap = properties.bootstrap();
        createIfMissing(
                bootstrap.operatorUsername(),
                bootstrap.operatorPassword(),
                UserRole.OPERATOR
        );
        createIfMissing(
                bootstrap.viewerUsername(),
                bootstrap.viewerPassword(),
                UserRole.VIEWER
        );
    }

    private void createIfMissing(String username, String password, UserRole role) {
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("Bootstrap usernames must not be blank");
        }
        if (password == null || password.length() < MINIMUM_PASSWORD_LENGTH) {
            throw new IllegalArgumentException("Bootstrap passwords must contain at least 12 characters");
        }
        if (userAccountRepository.findByUsernameIgnoreCase(username.trim()).isPresent()) {
            return;
        }
        Instant now = clock.instant();
        userAccountRepository.save(new UserAccount(
                UUID.randomUUID(),
                username,
                passwordEncoder.encode(password),
                role,
                now
        ));
    }
}
