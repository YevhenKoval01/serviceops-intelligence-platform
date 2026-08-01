package io.github.yevhenkoval.serviceops.api;

import io.github.yevhenkoval.serviceops.ticket.TicketService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@SecurityRequirement(name = "bearerAuth")
@PreAuthorize("hasAnyRole('VIEWER', 'OPERATOR')")
public class TicketController {

    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @Operation(
            summary = "Create a ticket",
            description = "Persists a ticket immediately and starts asynchronous classification after commit."
    )
    @ApiResponse(responseCode = "201", description = "Ticket created; prediction fields may still be null")
    @ApiResponse(responseCode = "400", description = "Request validation failed")
    @PostMapping("/tickets")
    @PreAuthorize("hasRole('OPERATOR')")
    ResponseEntity<TicketResponse> create(@Valid @RequestBody CreateTicketRequest request) {
        TicketResponse response = TicketResponse.from(ticketService.create(request));
        return ResponseEntity.created(URI.create("/api/tickets/" + response.id())).body(response);
    }

    @Operation(summary = "List tickets", description = "Returns newest tickets first.")
    @GetMapping("/tickets")
    List<TicketResponse> list() {
        return ticketService.list().stream().map(TicketResponse::from).toList();
    }

    @Operation(summary = "Get a ticket")
    @ApiResponse(responseCode = "404", description = "Ticket does not exist")
    @GetMapping("/tickets/{id}")
    TicketResponse get(@PathVariable UUID id) {
        return TicketResponse.from(ticketService.get(id));
    }

    @Operation(summary = "Update ticket status")
    @ApiResponse(responseCode = "404", description = "Ticket does not exist")
    @PatchMapping("/tickets/{id}/status")
    @PreAuthorize("hasRole('OPERATOR')")
    TicketResponse updateStatus(@PathVariable UUID id, @Valid @RequestBody UpdateStatusRequest request) {
        return TicketResponse.from(ticketService.updateStatus(id, request.status()));
    }

    @Operation(summary = "Get ticket queue totals by status")
    @GetMapping("/summary")
    SummaryResponse summary() {
        return ticketService.summary();
    }
}
