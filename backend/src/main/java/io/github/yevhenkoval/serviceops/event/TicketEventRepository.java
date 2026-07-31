package io.github.yevhenkoval.serviceops.event;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TicketEventRepository extends JpaRepository<TicketEvent, UUID> {

    @Query(value = """
            SELECT *
            FROM ticket_events
            WHERE published_at IS NULL
              AND next_attempt_at <= :now
            ORDER BY next_attempt_at, created_at, id
            LIMIT :batchSize
            FOR UPDATE SKIP LOCKED
            """, nativeQuery = true)
    List<TicketEvent> lockPendingForPublication(
            @Param("now") Instant now,
            @Param("batchSize") int batchSize
    );
}
