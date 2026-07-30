package io.github.yevhenkoval.serviceops.ticket;

import java.util.UUID;

public class TicketNotFoundException extends RuntimeException {

    public TicketNotFoundException(UUID id) {
        super("Ticket " + id + " was not found");
    }
}
