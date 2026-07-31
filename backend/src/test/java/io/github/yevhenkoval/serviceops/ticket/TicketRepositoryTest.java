package io.github.yevhenkoval.serviceops.ticket;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.event.TicketEvent;
import io.github.yevhenkoval.serviceops.event.TicketEventRepository;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
@DataJpaTest
class TicketRepositoryTest {

    @Container
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:17.5-alpine");

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    private TicketRepository ticketRepository;

    @Autowired
    private TicketEventRepository ticketEventRepository;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @Test
    void flywaySchemaPersistsTicketAndJsonEventTogether() {
        Instant now = Instant.parse("2026-07-30T10:00:00Z");
        UUID ticketId = UUID.randomUUID();
        UUID eventId = UUID.randomUUID();
        Ticket ticket = ticketRepository.saveAndFlush(new Ticket(
                ticketId,
                "VPN access unavailable",
                "The employee cannot reach internal systems through the corporate VPN.",
                Priority.HIGH,
                now
        ));
        var payload = objectMapper.createObjectNode()
                .put("eventId", eventId.toString())
                .put("eventType", "ticket.created");
        ticketEventRepository.saveAndFlush(new TicketEvent(
                eventId,
                ticketId,
                "ticket.created",
                payload,
                now
        ));

        assertThat(ticketRepository.findById(ticketId)).contains(ticket);
        assertThat(ticketRepository.findAllByOrderByCreatedAtDesc())
                .extracting(Ticket::getId)
                .containsExactly(ticketId);
        assertThat(ticketEventRepository.findById(eventId))
                .get()
                .extracting(TicketEvent::getEventPayload)
                .satisfies(json -> assertThat(json.get("eventType").asText()).isEqualTo("ticket.created"));
    }
}
