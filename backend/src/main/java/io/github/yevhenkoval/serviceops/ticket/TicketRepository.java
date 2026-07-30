package io.github.yevhenkoval.serviceops.ticket;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TicketRepository extends JpaRepository<Ticket, UUID> {

    List<Ticket> findAllByOrderByCreatedAtDesc();

    long countByStatus(TicketStatus status);
}
