package io.github.yevhenkoval.serviceops.ticket;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TicketLifecycleEventRepository extends JpaRepository<TicketLifecycleEvent, UUID> {

    List<TicketLifecycleEvent> findAllByTicketIdOrderByOccurredAtAscIdAsc(UUID ticketId);
}
