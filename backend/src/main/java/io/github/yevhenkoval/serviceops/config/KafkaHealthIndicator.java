package io.github.yevhenkoval.serviceops.config;

import java.time.Duration;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.Admin;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class KafkaHealthIndicator implements HealthIndicator {

    private final Admin admin;
    private final Duration timeout;

    public KafkaHealthIndicator(
            Admin admin,
            @Value("${serviceops.kafka.health-timeout:2s}") Duration timeout
    ) {
        this.admin = admin;
        this.timeout = timeout;
    }

    @Override
    public Health health() {
        try {
            String clusterId = admin.describeCluster().clusterId()
                    .get(timeout.toMillis(), TimeUnit.MILLISECONDS);
            return Health.up().withDetail("clusterId", clusterId).build();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return Health.down(exception).build();
        } catch (Exception exception) {
            return Health.down(exception).build();
        }
    }
}
