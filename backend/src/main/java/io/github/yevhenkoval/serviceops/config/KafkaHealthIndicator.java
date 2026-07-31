package io.github.yevhenkoval.serviceops.config;

import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.Admin;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class KafkaHealthIndicator implements HealthIndicator {

    private final Admin admin;

    public KafkaHealthIndicator(Admin admin) {
        this.admin = admin;
    }

    @Override
    public Health health() {
        try {
            String clusterId = admin.describeCluster().clusterId().get(2, TimeUnit.SECONDS);
            return Health.up().withDetail("clusterId", clusterId).build();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return Health.down(exception).build();
        } catch (Exception exception) {
            return Health.down(exception).build();
        }
    }
}
