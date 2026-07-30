package io.github.yevhenkoval.serviceops.ticket;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.api.CreateTicketRequest;
import io.github.yevhenkoval.serviceops.api.SummaryResponse;
import io.github.yevhenkoval.serviceops.event.EventEnvelope;
import io.github.yevhenkoval.serviceops.event.EventPublisher;
import io.github.yevhenkoval.serviceops.event.TicketEvent;
import io.github.yevhenkoval.serviceops.event.TicketEventRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Service
public class TicketService {

    private final TicketRepository ticketRepository;
    private final TicketEventRepository eventRepository;
    private final EventPublisher eventPublisher;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public TicketService(
            TicketRepository ticketRepository,
            TicketEventRepository eventRepository,
            EventPublisher eventPublisher,
            ObjectMapper objectMapper
    ) {
        this(ticketRepository, eventRepository, eventPublisher, objectMapper, Clock.systemUTC());
    }

    TicketService(
            TicketRepository ticketRepository,
            TicketEventRepository eventRepository,
            EventPublisher eventPublisher,
            ObjectMapper objectMapper,
            Clock clock
    ) {
        this.ticketRepository = ticketRepository;
        this.eventRepository = eventRepository;
        this.eventPublisher = eventPublisher;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    @Transactional
    public Ticket create(CreateTicketRequest request) {
        Instant now = clock.instant();
        UUID ticketId = UUID.randomUUID();
        Ticket ticket = ticketRepository.save(new Ticket(
                ticketId,
                request.title().trim(),
                request.description().trim(),
                request.reportedPriority(),
                now
        ));

        UUID eventId = UUID.randomUUID();
        var payload = objectMapper.createObjectNode()
                .put("title", ticket.getTitle())
                .put("description", ticket.getDescription());
        if (ticket.getReportedPriority() == null) {
            payload.putNull("reportedPriority");
        } else {
            payload.put("reportedPriority", ticket.getReportedPriority().name());
        }
        EventEnvelope event = new EventEnvelope(
                eventId,
                "ticket.created",
                1,
                now,
                eventId,
                ticketId,
                payload
        );
        eventRepository.save(new TicketEvent(
                eventId,
                ticketId,
                event.eventType(),
                objectMapper.valueToTree(event),
                now
        ));
        publishAfterCommit(event);
        return ticket;
    }

    @Transactional(readOnly = true)
    public List<Ticket> list() {
        return ticketRepository.findAllByOrderByCreatedAtDesc();
    }

    @Transactional(readOnly = true)
    public Ticket get(UUID id) {
        return ticketRepository.findById(id).orElseThrow(() -> new TicketNotFoundException(id));
    }

    @Transactional
    public Ticket updateStatus(UUID id, TicketStatus status) {
        Ticket ticket = ticketRepository.findById(id)
                .orElseThrow(() -> new TicketNotFoundException(id));
        ticket.updateStatus(status, clock.instant());
        return ticket;
    }

    @Transactional(readOnly = true)
    public SummaryResponse summary() {
        return new SummaryResponse(
                ticketRepository.count(),
                ticketRepository.countByStatus(TicketStatus.OPEN),
                ticketRepository.countByStatus(TicketStatus.IN_PROGRESS),
                ticketRepository.countByStatus(TicketStatus.RESOLVED)
        );
    }

    private void publishAfterCommit(EventEnvelope event) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    eventPublisher.publishTicketCreated(event);
                }
            });
        } else {
            eventPublisher.publishTicketCreated(event);
        }
    }
}
