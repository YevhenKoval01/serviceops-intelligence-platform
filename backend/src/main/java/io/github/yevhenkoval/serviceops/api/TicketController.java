package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.TicketService;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class TicketController {

    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @PostMapping("/tickets")
    ResponseEntity<TicketResponse> create(@Valid @RequestBody CreateTicketRequest request) {
        TicketResponse response = TicketResponse.from(ticketService.create(request));
        return ResponseEntity.created(URI.create("/api/tickets/" + response.id())).body(response);
    }

    @GetMapping("/tickets")
    List<TicketResponse> list() {
        return ticketService.list().stream().map(TicketResponse::from).toList();
    }

    @GetMapping("/tickets/{id}")
    TicketResponse get(@PathVariable UUID id) {
        return TicketResponse.from(ticketService.get(id));
    }

    @PatchMapping("/tickets/{id}/status")
    TicketResponse updateStatus(@PathVariable UUID id, @Valid @RequestBody UpdateStatusRequest request) {
        return TicketResponse.from(ticketService.updateStatus(id, request.status()));
    }

    @GetMapping("/summary")
    SummaryResponse summary() {
        return ticketService.summary();
    }
}
