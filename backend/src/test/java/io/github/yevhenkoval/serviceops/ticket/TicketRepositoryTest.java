package io.github.yevhenkoval.serviceops.ticket;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.auth.UserAccount;
import io.github.yevhenkoval.serviceops.auth.UserAccountRepository;
import io.github.yevhenkoval.serviceops.auth.UserRole;
import io.github.yevhenkoval.serviceops.event.TicketEvent;
import io.github.yevhenkoval.serviceops.event.TicketEventRepository;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
@DataJpaTest
class TicketRepositoryTest {

    @Container
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:17.5-alpine");

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    private TicketRepository ticketRepository;

    @Autowired
    private TicketEventRepository ticketEventRepository;

    @Autowired
    private TicketLifecycleEventRepository lifecycleEventRepository;

    @Autowired
    private UserAccountRepository userAccountRepository;

    @Autowired
    private PlatformTransactionManager transactionManager;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @Test
    void flywaySchemaPersistsAuthenticationAccounts() {
        Instant now = Instant.parse("2026-08-01T10:00:00Z");
        UserAccount account = userAccountRepository.saveAndFlush(new UserAccount(
                UUID.randomUUID(),
                "Viewer",
                "$2a$10$nonSensitiveTestPasswordHashValue000000000000000000000000",
                UserRole.VIEWER,
                now
        ));

        assertThat(userAccountRepository.findByUsernameIgnoreCase("VIEWER"))
                .contains(account)
                .get()
                .satisfies(stored -> {
                    assertThat(stored.getUsername()).isEqualTo("viewer");
                    assertThat(stored.getRole()).isEqualTo(UserRole.VIEWER);
                    assertThat(stored.isEnabled()).isTrue();
                });
    }

    @Test
    void flywaySchemaPersistsTicketAndJsonEventTogether() {
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        UUID ticketId = UUID.randomUUID();
        UUID eventId = UUID.randomUUID();
        Ticket ticket = ticketRepository.saveAndFlush(new Ticket(
                ticketId,
                "VPN access unavailable",
                "The employee cannot reach internal systems through the corporate VPN.",
                Priority.HIGH,
                now
        ));
        var payload = objectMapper.createObjectNode()
                .put("eventId", eventId.toString())
                .put("eventType", "ticket.created");
        ticketEventRepository.saveAndFlush(new TicketEvent(
                eventId,
                ticketId,
                "ticket.created",
                payload,
                now
        ));

        assertThat(ticketRepository.findById(ticketId)).contains(ticket);
        assertThat(ticketRepository.findAllByOrderByCreatedAtDesc())
                .extracting(Ticket::getId)
                .containsExactly(ticketId);
        assertThat(ticketEventRepository.findById(eventId))
                .get()
                .extracting(TicketEvent::getEventPayload)
                .satisfies(json -> assertThat(json.get("eventType").asText()).isEqualTo("ticket.created"));
        assertThat(ticketEventRepository.findById(eventId))
                .get()
                .satisfies(event -> {
                    assertThat(event.isPublished()).isFalse();
                    assertThat(event.getPublishAttempts()).isZero();
                    assertThat(event.getNextAttemptAt()).isEqualTo(now);
                });
    }

    @Test
    void flywaySchemaPersistsOrderedLifecycleHistory() {
        Instant now = Instant.parse("2026-08-04T10:00:00Z");
        UUID ticketId = UUID.randomUUID();
        ticketRepository.saveAndFlush(new Ticket(
                ticketId,
                "Analytics lifecycle validation",
                "Status transitions must be retained in timestamp order for the analytics models.",
                Priority.MEDIUM,
                now
        ));
        lifecycleEventRepository.saveAllAndFlush(List.of(
                new TicketLifecycleEvent(
                        UUID.randomUUID(),
                        ticketId,
                        TicketLifecycleEventType.CREATED,
                        null,
                        TicketStatus.OPEN,
                        now
                ),
                new TicketLifecycleEvent(
                        UUID.randomUUID(),
                        ticketId,
                        TicketLifecycleEventType.STATUS_CHANGED,
                        TicketStatus.OPEN,
                        TicketStatus.IN_PROGRESS,
                        now.plusSeconds(900)
                )
        ));

        assertThat(lifecycleEventRepository.findAllByTicketIdOrderByOccurredAtAscIdAsc(ticketId))
                .extracting(TicketLifecycleEvent::getCurrentStatus)
                .containsExactly(TicketStatus.OPEN, TicketStatus.IN_PROGRESS);
    }

    @Test
    void locksOnlyDueUnpublishedOutboxEvents() {
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        UUID ticketId = UUID.randomUUID();
        ticketRepository.saveAndFlush(new Ticket(
                ticketId,
                "Warehouse scanner outage",
                "All warehouse scanners are unable to connect to the inventory service.",
                Priority.HIGH,
                now
        ));

        TicketEvent due = event(ticketId, now);
        TicketEvent delayed = event(ticketId, now.plusMillis(1));
        delayed.markPublicationFailed(now.plusSeconds(30), "broker unavailable");
        TicketEvent published = event(ticketId, now.plusMillis(2));
        published.markPublished(now.plusSeconds(1));
        ticketEventRepository.saveAllAndFlush(List.of(due, delayed, published));

        assertThat(ticketEventRepository.lockPendingForPublication(now.plusSeconds(1), 10))
                .extracting(TicketEvent::getId)
                .containsExactly(due.getId());
    }

    @Test
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    void skipsRowsLockedByAnotherRelayTransaction() throws Exception {
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        UUID ticketId = UUID.randomUUID();
        UUID eventId = new TransactionTemplate(transactionManager).execute(status -> {
            ticketRepository.save(new Ticket(
                    ticketId,
                    "Concurrent outbox relay check",
                    "Two relay transactions must not publish the same event concurrently.",
                    Priority.MEDIUM,
                    now
            ));
            return ticketEventRepository.save(event(ticketId, now)).getId();
        });
        CountDownLatch rowLocked = new CountDownLatch(1);
        CountDownLatch releaseLock = new CountDownLatch(1);
        var executor = Executors.newSingleThreadExecutor();

        try {
            var lockHolder = executor.submit(() -> new TransactionTemplate(transactionManager).execute(status -> {
                var locked = ticketEventRepository.lockPendingForPublication(now.plusSeconds(1), 10);
                rowLocked.countDown();
                await(releaseLock);
                return locked.stream().map(TicketEvent::getId).toList();
            }));

            assertThat(rowLocked.await(10, TimeUnit.SECONDS)).isTrue();
            var skipped = new TransactionTemplate(transactionManager).execute(
                    status -> ticketEventRepository.lockPendingForPublication(now.plusSeconds(1), 10)
            );
            assertThat(skipped).isEmpty();

            releaseLock.countDown();
            assertThat(lockHolder.get(10, TimeUnit.SECONDS)).containsExactly(eventId);
        } finally {
            releaseLock.countDown();
            executor.shutdownNow();
            new TransactionTemplate(transactionManager).executeWithoutResult(status -> {
                ticketEventRepository.deleteById(eventId);
                ticketRepository.deleteById(ticketId);
            });
        }
    }

    private TicketEvent event(UUID ticketId, Instant createdAt) {
        UUID eventId = UUID.randomUUID();
        var payload = objectMapper.createObjectNode()
                .put("eventId", eventId.toString())
                .put("eventType", "ticket.created");
        return new TicketEvent(eventId, ticketId, "ticket.created", payload, createdAt);
    }

    private void await(CountDownLatch latch) {
        try {
            if (!latch.await(10, TimeUnit.SECONDS)) {
                throw new IllegalStateException("Timed out waiting to release outbox row lock");
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while holding outbox row lock", exception);
        }
    }
}
