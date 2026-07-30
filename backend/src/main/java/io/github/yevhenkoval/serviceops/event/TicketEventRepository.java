package io.github.yevhenkoval.serviceops.event;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TicketEventRepository extends JpaRepository<TicketEvent, UUID> {
}
