package io.github.yevhenkoval.serviceops.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;

class EventPublisherTest {

    private static final String TOPIC = "serviceops.ticket.created.v1";

    @Test
    void waitsForBrokerAcknowledgementAndPublishesStoredEnvelope() throws Exception {
        KafkaTemplate<String, String> kafkaTemplate = kafkaTemplate();
        when(kafkaTemplate.send(eq(TOPIC), anyString(), anyString()))
                .thenReturn(CompletableFuture.completedFuture(null));
        var publisher = new EventPublisher(kafkaTemplate, new ObjectMapper(), TOPIC, 1000);
        TicketEvent event = event();

        publisher.publishTicketCreated(event);

        ArgumentCaptor<String> payload = ArgumentCaptor.forClass(String.class);
        verify(kafkaTemplate).send(eq(TOPIC), eq(event.getTicketId().toString()), payload.capture());
        assertThat(new ObjectMapper().readTree(payload.getValue()).get("eventId").asText())
                .isEqualTo(event.getId().toString());
    }

    @Test
    void failsWhenKafkaDoesNotAcknowledgeTheEvent() {
        KafkaTemplate<String, String> kafkaTemplate = kafkaTemplate();
        CompletableFuture<SendResult<String, String>> failed = new CompletableFuture<>();
        failed.completeExceptionally(new IllegalStateException("broker unavailable"));
        when(kafkaTemplate.send(eq(TOPIC), anyString(), anyString())).thenReturn(failed);
        var publisher = new EventPublisher(kafkaTemplate, new ObjectMapper(), TOPIC, 1000);

        assertThatThrownBy(() -> publisher.publishTicketCreated(event()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("Kafka did not acknowledge ticket event")
                .hasRootCauseMessage("broker unavailable");
    }

    @SuppressWarnings("unchecked")
    private KafkaTemplate<String, String> kafkaTemplate() {
        return mock(KafkaTemplate.class);
    }

    private TicketEvent event() {
        UUID eventId = UUID.randomUUID();
        UUID ticketId = UUID.randomUUID();
        var payload = new ObjectMapper().createObjectNode()
                .put("eventId", eventId.toString())
                .put("eventType", "ticket.created")
                .put("ticketId", ticketId.toString());
        return new TicketEvent(eventId, ticketId, "ticket.created", payload, Instant.parse("2026-07-30T10:00:00Z"));
    }
}
