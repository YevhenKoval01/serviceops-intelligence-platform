package io.github.yevhenkoval.serviceops.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.core.KafkaTemplate;

class InvalidEventPublisherTest {

    @Test
    void createsStructuredDeadLetterRecordWithSourceCoordinates() throws Exception {
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = mock(KafkaTemplate.class);
        var publisher = new InvalidEventPublisher(
                kafkaTemplate,
                new ObjectMapper(),
                "serviceops.ticket.invalid.v1",
                Clock.fixed(Instant.parse("2026-07-30T10:00:00Z"), ZoneOffset.UTC)
        );
        var source = new ConsumerRecord<String, String>(
                "serviceops.ticket.prediction-completed.v1",
                0,
                42L,
                "ticket-key",
                "{\"eventType\":\"wrong\"}"
        );

        var invalid = new ObjectMapper().readTree(
                publisher.createInvalidEvent(source, new IllegalArgumentException("contract mismatch"))
        );

        assertThat(invalid.get("failedAt").asText()).isEqualTo("2026-07-30T10:00:00Z");
        assertThat(invalid.get("reason").asText()).isEqualTo("contract mismatch");
        assertThat(invalid.get("sourceTopic").asText())
                .isEqualTo("serviceops.ticket.prediction-completed.v1");
        assertThat(invalid.get("sourcePartition").asInt()).isZero();
        assertThat(invalid.get("sourceOffset").asLong()).isEqualTo(42L);
        assertThat(invalid.get("originalMessage").asText()).contains("\"eventType\":\"wrong\"");
    }
}
