package io.github.yevhenkoval.serviceops.event;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.ticket.Priority;
import io.github.yevhenkoval.serviceops.ticket.TicketNotFoundException;
import io.github.yevhenkoval.serviceops.ticket.TicketRepository;
import java.math.BigDecimal;
import java.time.Clock;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class PredictionEventConsumer {

    private static final Set<String> CATEGORIES = Set.of("ACCESS", "BILLING", "DELIVERY", "TECHNICAL");
    private static final Set<String> EVENT_FIELDS = Set.of(
            "eventId",
            "eventType",
            "eventVersion",
            "occurredAt",
            "correlationId",
            "ticketId",
            "payload"
    );
    private static final Set<String> PAYLOAD_FIELDS = Set.of(
            "category",
            "priority",
            "confidence",
            "modelVersion"
    );

    private final ObjectMapper objectMapper;
    private final TicketRepository ticketRepository;
    private final ProcessedEventRepository processedEventRepository;
    private final Clock clock;

    @Autowired
    public PredictionEventConsumer(
            ObjectMapper objectMapper,
            TicketRepository ticketRepository,
            ProcessedEventRepository processedEventRepository
    ) {
        this(objectMapper, ticketRepository, processedEventRepository, Clock.systemUTC());
    }

    PredictionEventConsumer(
            ObjectMapper objectMapper,
            TicketRepository ticketRepository,
            ProcessedEventRepository processedEventRepository,
            Clock clock
    ) {
        this.objectMapper = objectMapper;
        this.ticketRepository = ticketRepository;
        this.processedEventRepository = processedEventRepository;
        this.clock = clock;
    }

    @KafkaListener(topics = "${serviceops.topics.prediction-completed}")
    @Transactional
    public void consume(String message) {
        EventEnvelope event = parse(message);
        validate(event);
        if (processedEventRepository.existsById(event.eventId())) {
            return;
        }

        JsonNode payload = event.payload();
        var ticket = ticketRepository.findById(event.ticketId())
                .orElseThrow(() -> new TicketNotFoundException(event.ticketId()));
        ticket.applyPrediction(
                payload.get("category").asText(),
                Priority.valueOf(payload.get("priority").asText()),
                payload.get("confidence").decimalValue(),
                payload.get("modelVersion").asText(),
                clock.instant()
        );
        processedEventRepository.save(new ProcessedEvent(event.eventId(), clock.instant()));
    }

    private EventEnvelope parse(String message) {
        try {
            JsonNode root = objectMapper.readTree(message);
            if (!hasExactFields(root, EVENT_FIELDS)) {
                throw new IllegalArgumentException("Prediction event does not match contract v1");
            }
            return objectMapper.treeToValue(root, EventEnvelope.class);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Prediction event is not valid JSON", exception);
        }
    }

    private void validate(EventEnvelope event) {
        JsonNode payload = event.payload();
        if (!"ticket.prediction-completed".equals(event.eventType())
                || event.eventVersion() != 1
                || event.eventId() == null
                || event.ticketId() == null
                || event.correlationId() == null
                || event.occurredAt() == null
                || payload == null
                || !hasExactFields(payload, PAYLOAD_FIELDS)
                || !payload.hasNonNull("category")
                || !CATEGORIES.contains(payload.get("category").asText())
                || !payload.hasNonNull("priority")
                || !isPriority(payload.get("priority").asText())
                || !payload.hasNonNull("confidence")
                || !isConfidence(payload.get("confidence"))
                || !payload.hasNonNull("modelVersion")
                || !payload.get("modelVersion").isTextual()
                || payload.get("modelVersion").asText().isBlank()) {
            throw new IllegalArgumentException("Prediction event does not match contract v1");
        }
    }

    private boolean hasExactFields(JsonNode node, Set<String> expected) {
        if (node == null || !node.isObject()) {
            return false;
        }
        Set<String> actual = new HashSet<>();
        node.fieldNames().forEachRemaining(actual::add);
        return actual.equals(expected);
    }

    private boolean isPriority(String value) {
        try {
            Priority.valueOf(value);
            return true;
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    private boolean isConfidence(JsonNode value) {
        if (!value.isNumber()) {
            return false;
        }
        BigDecimal confidence = value.decimalValue();
        return confidence.compareTo(BigDecimal.ZERO) >= 0 && confidence.compareTo(BigDecimal.ONE) <= 0;
    }
}
