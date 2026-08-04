package io.github.yevhenkoval.serviceops.ticket;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.yevhenkoval.serviceops.api.CreateTicketRequest;
import io.github.yevhenkoval.serviceops.api.SummaryResponse;
import io.github.yevhenkoval.serviceops.event.EventEnvelope;
import io.github.yevhenkoval.serviceops.event.TicketEvent;
import io.github.yevhenkoval.serviceops.event.TicketEventRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TicketService {

    private final TicketRepository ticketRepository;
    private final TicketEventRepository eventRepository;
    private final TicketLifecycleEventRepository lifecycleEventRepository;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public TicketService(
            TicketRepository ticketRepository,
            TicketEventRepository eventRepository,
            TicketLifecycleEventRepository lifecycleEventRepository,
            ObjectMapper objectMapper
    ) {
        this(ticketRepository, eventRepository, lifecycleEventRepository, objectMapper, Clock.systemUTC());
    }

    TicketService(
            TicketRepository ticketRepository,
            TicketEventRepository eventRepository,
            TicketLifecycleEventRepository lifecycleEventRepository,
            ObjectMapper objectMapper,
            Clock clock
    ) {
        this.ticketRepository = ticketRepository;
        this.eventRepository = eventRepository;
        this.lifecycleEventRepository = lifecycleEventRepository;
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
        lifecycleEventRepository.save(new TicketLifecycleEvent(
                UUID.randomUUID(),
                ticketId,
                TicketLifecycleEventType.CREATED,
                null,
                TicketStatus.OPEN,
                now
        ));
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
        TicketStatus previousStatus = ticket.getStatus();
        if (previousStatus == status) {
            return ticket;
        }
        Instant now = clock.instant();
        ticket.updateStatus(status, now);
        TicketLifecycleEventType eventType = previousStatus == TicketStatus.RESOLVED
                ? TicketLifecycleEventType.REOPENED
                : TicketLifecycleEventType.STATUS_CHANGED;
        lifecycleEventRepository.save(new TicketLifecycleEvent(
                UUID.randomUUID(),
                id,
                eventType,
                previousStatus,
                status,
                now
        ));
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

}
