package io.github.yevhenkoval.serviceops.event;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
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

    public EventPublisher(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${serviceops.topics.ticket-created}") String ticketCreatedTopic
    ) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.ticketCreatedTopic = ticketCreatedTopic;
    }

    public void publishTicketCreated(EventEnvelope event) {
        try {
            String message = objectMapper.writeValueAsString(event);
            kafkaTemplate.send(ticketCreatedTopic, event.ticketId().toString(), message)
                    .whenComplete((result, error) -> {
                        if (error == null) {
                            log.info("Published {} for ticket {}", event.eventType(), event.ticketId());
                        } else {
                            log.error("Failed to publish event {}", event.eventId(), error);
                        }
                    });
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Could not serialize ticket event", exception);
        }
    }
}
