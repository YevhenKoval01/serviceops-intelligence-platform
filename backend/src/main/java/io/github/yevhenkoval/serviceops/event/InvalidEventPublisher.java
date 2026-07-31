package io.github.yevhenkoval.serviceops.event;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class InvalidEventPublisher {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final String invalidTopic;
    private final Clock clock;

    @Autowired
    public InvalidEventPublisher(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${serviceops.topics.invalid}") String invalidTopic
    ) {
        this(kafkaTemplate, objectMapper, invalidTopic, Clock.systemUTC());
    }

    InvalidEventPublisher(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            String invalidTopic,
            Clock clock
    ) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.invalidTopic = invalidTopic;
        this.clock = clock;
    }

    public void publish(ConsumerRecord<?, ?> record, Exception exception) {
        String key = record.key() == null ? null : record.key().toString();
        kafkaTemplate.send(invalidTopic, key, createInvalidEvent(record, exception)).join();
    }

    String createInvalidEvent(ConsumerRecord<?, ?> record, Exception exception) {
        var invalid = objectMapper.createObjectNode()
                .put("failedAt", clock.instant().toString())
                .put("reason", rootMessage(exception))
                .put("sourceTopic", record.topic())
                .put("sourcePartition", record.partition())
                .put("sourceOffset", record.offset());
        if (record.value() == null) {
            invalid.putNull("originalMessage");
        } else {
            invalid.put("originalMessage", record.value().toString());
        }
        try {
            return objectMapper.writeValueAsString(invalid);
        } catch (JsonProcessingException serializationError) {
            throw new IllegalStateException("Could not serialize invalid event record", serializationError);
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
