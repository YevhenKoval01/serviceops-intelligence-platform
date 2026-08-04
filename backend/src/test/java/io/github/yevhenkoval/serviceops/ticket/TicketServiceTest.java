package io.github.yevhenkoval.serviceops.ticket;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.api.CreateTicketRequest;
import io.github.yevhenkoval.serviceops.event.TicketEvent;
import io.github.yevhenkoval.serviceops.event.TicketEventRepository;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class TicketServiceTest {

    @Mock
    private TicketRepository ticketRepository;

    @Mock
    private TicketEventRepository eventRepository;

    @Mock
    private TicketLifecycleEventRepository lifecycleEventRepository;

    @Test
    void createsTicketAndStoresUnpublishedOutboxEventInTheSameTransaction() {
        when(ticketRepository.save(any(Ticket.class))).thenAnswer(invocation -> invocation.getArgument(0));
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        var service = new TicketService(
                ticketRepository,
                eventRepository,
                lifecycleEventRepository,
                new ObjectMapper().findAndRegisterModules(),
                Clock.fixed(now, ZoneOffset.UTC)
        );

        Ticket ticket = service.create(new CreateTicketRequest(
                "VPN access fails",
                "The employee cannot connect to the corporate VPN.",
                Priority.HIGH
        ));

        assertThat(ticket.getStatus()).isEqualTo(TicketStatus.OPEN);
        assertThat(ticket.getCreatedAt()).isEqualTo(now);
        ArgumentCaptor<TicketEvent> eventCaptor = ArgumentCaptor.forClass(TicketEvent.class);
        verify(eventRepository).save(eventCaptor.capture());
        TicketEvent event = eventCaptor.getValue();
        assertThat(event.getEventType()).isEqualTo("ticket.created");
        assertThat(event.getTicketId()).isEqualTo(ticket.getId());
        assertThat(event.getEventPayload().get("payload").get("title").asText())
                .isEqualTo("VPN access fails");
        assertThat(event.isPublished()).isFalse();
        assertThat(event.getPublishAttempts()).isZero();
        assertThat(event.getNextAttemptAt()).isEqualTo(now);
        ArgumentCaptor<TicketLifecycleEvent> lifecycleCaptor =
                ArgumentCaptor.forClass(TicketLifecycleEvent.class);
        verify(lifecycleEventRepository).save(lifecycleCaptor.capture());
        assertThat(lifecycleCaptor.getValue()).satisfies(lifecycle -> {
            assertThat(lifecycle.getTicketId()).isEqualTo(ticket.getId());
            assertThat(lifecycle.getEventType()).isEqualTo(TicketLifecycleEventType.CREATED);
            assertThat(lifecycle.getPreviousStatus()).isNull();
            assertThat(lifecycle.getCurrentStatus()).isEqualTo(TicketStatus.OPEN);
            assertThat(lifecycle.getOccurredAt()).isEqualTo(now);
        });
    }

    @Test
    void recordsStatusTransitionsAndReopens() {
        Instant createdAt = Instant.parse("2026-07-30T09:00:00Z");
        Instant changedAt = Instant.parse("2026-07-30T10:00:00Z");
        Ticket ticket = new Ticket(
                UUID.randomUUID(),
                "VPN access fails",
                "The employee cannot connect to the corporate VPN.",
                Priority.HIGH,
                createdAt
        );
        ticket.updateStatus(TicketStatus.RESOLVED, createdAt.plusSeconds(1800));
        when(ticketRepository.findById(ticket.getId())).thenReturn(java.util.Optional.of(ticket));
        var service = new TicketService(
                ticketRepository,
                eventRepository,
                lifecycleEventRepository,
                new ObjectMapper().findAndRegisterModules(),
                Clock.fixed(changedAt, ZoneOffset.UTC)
        );

        service.updateStatus(ticket.getId(), TicketStatus.OPEN);

        ArgumentCaptor<TicketLifecycleEvent> lifecycleCaptor =
                ArgumentCaptor.forClass(TicketLifecycleEvent.class);
        verify(lifecycleEventRepository).save(lifecycleCaptor.capture());
        assertThat(lifecycleCaptor.getValue()).satisfies(lifecycle -> {
            assertThat(lifecycle.getEventType()).isEqualTo(TicketLifecycleEventType.REOPENED);
            assertThat(lifecycle.getPreviousStatus()).isEqualTo(TicketStatus.RESOLVED);
            assertThat(lifecycle.getCurrentStatus()).isEqualTo(TicketStatus.OPEN);
            assertThat(lifecycle.getOccurredAt()).isEqualTo(changedAt);
        });
    }

    @Test
    void ignoresNoOpStatusChanges() {
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        Ticket ticket = new Ticket(
                UUID.randomUUID(),
                "VPN access fails",
                "The employee cannot connect to the corporate VPN.",
                Priority.HIGH,
                now
        );
        when(ticketRepository.findById(ticket.getId())).thenReturn(java.util.Optional.of(ticket));
        var service = new TicketService(
                ticketRepository,
                eventRepository,
                lifecycleEventRepository,
                new ObjectMapper().findAndRegisterModules(),
                Clock.fixed(now.plusSeconds(60), ZoneOffset.UTC)
        );

        Ticket unchanged = service.updateStatus(ticket.getId(), TicketStatus.OPEN);

        assertThat(unchanged.getUpdatedAt()).isEqualTo(now);
        verifyNoInteractions(lifecycleEventRepository);
    }
}
