package io.github.yevhenkoval.serviceops.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.ticket.Ticket;
import io.github.yevhenkoval.serviceops.ticket.TicketRepository;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class PredictionEventConsumerTest {

    @Mock
    private TicketRepository ticketRepository;

    @Mock
    private ProcessedEventRepository processedEventRepository;

    private PredictionEventConsumer consumer;

    @BeforeEach
    void setUp() {
        consumer = new PredictionEventConsumer(
                new ObjectMapper().findAndRegisterModules(),
                ticketRepository,
                processedEventRepository
        );
    }

    @Test
    void appliesValidPredictionAndRecordsIdempotencyKey() {
        UUID ticketId = UUID.randomUUID();
        UUID eventId = UUID.randomUUID();
        Ticket ticket = new Ticket(
                ticketId,
                "Application crashes",
                "Desktop application crashes during startup.",
                null,
                Instant.now()
        );
        when(ticketRepository.findById(ticketId)).thenReturn(Optional.of(ticket));
        when(processedEventRepository.existsById(eventId)).thenReturn(false);

        consumer.consume(eventJson(eventId, ticketId));

        assertThat(ticket.getPredictedCategory()).isEqualTo("TECHNICAL");
        assertThat(ticket.getPredictedPriority().name()).isEqualTo("HIGH");
        assertThat(ticket.getPredictionConfidence()).isEqualByComparingTo("0.91");
        verify(processedEventRepository).save(any(ProcessedEvent.class));
    }

    @Test
    void ignoresAlreadyProcessedEvent() {
        UUID ticketId = UUID.randomUUID();
        UUID eventId = UUID.randomUUID();
        when(processedEventRepository.existsById(eventId)).thenReturn(true);

        consumer.consume(eventJson(eventId, ticketId));

        verify(ticketRepository, never()).findById(any());
    }

    @Test
    void rejectsMalformedEvent() {
        assertThatThrownBy(() -> consumer.consume("{\"eventType\":\"wrong\"}"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private String eventJson(UUID eventId, UUID ticketId) {
        return """
                {
                  "eventId": "%s",
                  "eventType": "ticket.prediction-completed",
                  "eventVersion": 1,
                  "occurredAt": "2026-07-30T10:00:00Z",
                  "correlationId": "%s",
                  "ticketId": "%s",
                  "payload": {
                    "category": "TECHNICAL",
                    "priority": "HIGH",
                    "confidence": 0.91,
                    "modelVersion": "baseline-1"
                  }
                }
                """.formatted(eventId, eventId, ticketId);
    }
}
