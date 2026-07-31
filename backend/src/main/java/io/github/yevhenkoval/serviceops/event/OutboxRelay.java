package io.github.yevhenkoval.serviceops.event;

import java.time.Clock;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(prefix = "serviceops.outbox", name = "enabled", havingValue = "true", matchIfMissing = true)
public class OutboxRelay {

    private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);

    private final TicketEventRepository eventRepository;
    private final EventPublisher eventPublisher;
    private final int batchSize;
    private final long initialBackoffMs;
    private final long maxBackoffMs;
    private final Clock clock;

    @Autowired
    public OutboxRelay(
            TicketEventRepository eventRepository,
            EventPublisher eventPublisher,
            @Value("${serviceops.outbox.batch-size:25}") int batchSize,
            @Value("${serviceops.outbox.initial-backoff-ms:1000}") long initialBackoffMs,
            @Value("${serviceops.outbox.max-backoff-ms:60000}") long maxBackoffMs
    ) {
        this(
                eventRepository,
                eventPublisher,
                batchSize,
                initialBackoffMs,
                maxBackoffMs,
                Clock.systemUTC()
        );
    }

    OutboxRelay(
            TicketEventRepository eventRepository,
            EventPublisher eventPublisher,
            int batchSize,
            long initialBackoffMs,
            long maxBackoffMs,
            Clock clock
    ) {
        this.eventRepository = eventRepository;
        this.eventPublisher = eventPublisher;
        this.batchSize = Math.max(1, batchSize);
        this.initialBackoffMs = Math.max(1, initialBackoffMs);
        this.maxBackoffMs = Math.max(this.initialBackoffMs, maxBackoffMs);
        this.clock = clock;
    }

    @Scheduled(
            fixedDelayString = "${serviceops.outbox.poll-interval-ms:500}",
            initialDelayString = "${serviceops.outbox.initial-delay-ms:1000}"
    )
    @Transactional
    public int publishPendingBatch() {
        Instant queryTime = clock.instant();
        var events = eventRepository.lockPendingForPublication(queryTime, batchSize);
        int attempted = 0;
        for (TicketEvent event : events) {
            attempted += 1;
            if (!publish(event)) {
                break;
            }
        }
        return attempted;
    }

    private boolean publish(TicketEvent event) {
        try {
            eventPublisher.publishTicketCreated(event);
            event.markPublished(clock.instant());
            return true;
        } catch (Exception exception) {
            long retryDelayMs = retryDelayMs(event.getPublishAttempts());
            String error = rootMessage(exception);
            event.markPublicationFailed(clock.instant().plusMillis(retryDelayMs), error);
            log.warn(
                    "Outbox publication failed for event {}; retrying in {} ms: {}",
                    event.getId(),
                    retryDelayMs,
                    error
            );
            log.debug("Outbox publication failure details for event {}", event.getId(), exception);
            return false;
        }
    }

    long retryDelayMs(int completedAttempts) {
        int exponent = Math.min(Math.max(0, completedAttempts), 20);
        try {
            return Math.min(Math.multiplyExact(initialBackoffMs, 1L << exponent), maxBackoffMs);
        } catch (ArithmeticException ignored) {
            return maxBackoffMs;
        }
    }

    private String rootMessage(Exception exception) {
        Throwable cause = exception;
        while (cause.getCause() != null) {
            cause = cause.getCause();
        }
        return cause.getMessage() == null ? cause.getClass().getSimpleName() : cause.getMessage();
    }
}
