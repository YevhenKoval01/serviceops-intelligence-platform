package io.github.yevhenkoval.serviceops.ticket;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.api.CreateTicketRequest;
import io.github.yevhenkoval.serviceops.event.EventEnvelope;
import io.github.yevhenkoval.serviceops.event.EventPublisher;
import io.github.yevhenkoval.serviceops.event.TicketEventRepository;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
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
    private EventPublisher eventPublisher;

    @Test
    void createsTicketStoresEventAndPublishesContract() {
        when(ticketRepository.save(any(Ticket.class))).thenAnswer(invocation -> invocation.getArgument(0));
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        var service = new TicketService(
                ticketRepository,
                eventRepository,
                eventPublisher,
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
        verify(eventRepository).save(any());
        ArgumentCaptor<EventEnvelope> eventCaptor = ArgumentCaptor.forClass(EventEnvelope.class);
        verify(eventPublisher).publishTicketCreated(eventCaptor.capture());
        assertThat(eventCaptor.getValue().eventType()).isEqualTo("ticket.created");
        assertThat(eventCaptor.getValue().ticketId()).isEqualTo(ticket.getId());
        assertThat(eventCaptor.getValue().payload().get("title").asText()).isEqualTo("VPN access fails");
    }
}
