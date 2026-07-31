package io.github.yevhenkoval.serviceops.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OutboxRelayTest {

    private static final Instant NOW = Instant.parse("2026-07-30T10:00:00Z");

    @Test
    void marksEventPublishedOnlyAfterAcknowledgedDelivery() {
        TicketEventRepository repository = mock(TicketEventRepository.class);
        EventPublisher publisher = mock(EventPublisher.class);
        TicketEvent event = event();
        when(repository.lockPendingForPublication(NOW, 25)).thenReturn(List.of(event));
        OutboxRelay relay = relay(repository, publisher);

        assertThat(relay.publishPendingBatch()).isEqualTo(1);

        verify(publisher).publishTicketCreated(event);
        assertThat(event.isPublished()).isTrue();
        assertThat(event.getPublishedAt()).isEqualTo(NOW);
        assertThat(event.getPublishAttempts()).isEqualTo(1);
        assertThat(event.getLastPublishError()).isNull();
    }

    @Test
    void keepsFailedEventPendingWithBoundedExponentialBackoff() {
        TicketEventRepository repository = mock(TicketEventRepository.class);
        EventPublisher publisher = mock(EventPublisher.class);
        TicketEvent event = event();
        TicketEvent untouched = event();
        when(repository.lockPendingForPublication(NOW, 25)).thenReturn(List.of(event, untouched));
        doThrow(new IllegalStateException("broker unavailable"))
                .when(publisher).publishTicketCreated(event);
        OutboxRelay relay = relay(repository, publisher);

        assertThat(relay.publishPendingBatch()).isEqualTo(1);

        assertThat(event.isPublished()).isFalse();
        assertThat(event.getPublishAttempts()).isEqualTo(1);
        assertThat(event.getNextAttemptAt()).isEqualTo(NOW.plusSeconds(1));
        assertThat(event.getLastPublishError()).isEqualTo("broker unavailable");
        verify(publisher, never()).publishTicketCreated(untouched);

        relay.publishPendingBatch();
        assertThat(event.getPublishAttempts()).isEqualTo(2);
        assertThat(event.getNextAttemptAt()).isEqualTo(NOW.plusSeconds(2));
        assertThat(relay.retryDelayMs(20)).isEqualTo(60_000);
    }

    private OutboxRelay relay(TicketEventRepository repository, EventPublisher publisher) {
        return new OutboxRelay(
                repository,
                publisher,
                25,
                1000,
                60_000,
                Clock.fixed(NOW, ZoneOffset.UTC)
        );
    }

    private TicketEvent event() {
        UUID eventId = UUID.randomUUID();
        UUID ticketId = UUID.randomUUID();
        var payload = new ObjectMapper().createObjectNode()
                .put("eventId", eventId.toString())
                .put("eventType", "ticket.created")
                .put("ticketId", ticketId.toString());
        return new TicketEvent(eventId, ticketId, "ticket.created", payload, NOW);
    }
}
