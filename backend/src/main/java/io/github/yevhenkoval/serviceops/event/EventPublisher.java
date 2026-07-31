package io.github.yevhenkoval.serviceops.event;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class EventPublisher {

    private static final Logger log = LoggerFactory.getLogger(EventPublisher.class);

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final String ticketCreatedTopic;
    private final long sendTimeoutMs;

    public EventPublisher(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${serviceops.topics.ticket-created}") String ticketCreatedTopic,
            @Value("${serviceops.outbox.send-timeout-ms:10000}") long sendTimeoutMs
    ) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.ticketCreatedTopic = ticketCreatedTopic;
        this.sendTimeoutMs = sendTimeoutMs;
    }

    public void publishTicketCreated(TicketEvent event) {
        try {
            String message = objectMapper.writeValueAsString(event.getEventPayload());
            kafkaTemplate.send(ticketCreatedTopic, event.getTicketId().toString(), message)
                    .get(sendTimeoutMs, TimeUnit.MILLISECONDS);
            log.info("Published {} for ticket {}", event.getEventType(), event.getTicketId());
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Could not serialize ticket event", exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while publishing ticket event", exception);
        } catch (ExecutionException | TimeoutException exception) {
            throw new IllegalStateException("Kafka did not acknowledge ticket event", exception);
        }
    }
}
