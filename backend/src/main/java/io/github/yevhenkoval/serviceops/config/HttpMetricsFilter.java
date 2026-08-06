package io.github.yevhenkoval.serviceops.config;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerMapping;

@Component
public class HttpMetricsFilter extends OncePerRequestFilter {

    private static final String SERVICE_NAME = "serviceops-backend";

    private final MeterRegistry meterRegistry;

    public HttpMetricsFilter(Optional<MeterRegistry> meterRegistry) {
        this.meterRegistry = meterRegistry.orElse(null);
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        long startedAt = System.nanoTime();
        try {
            filterChain.doFilter(request, response);
        } finally {
            if (meterRegistry != null) {
                recordMetrics(request, response, startedAt);
            }
        }
    }

    private void recordMetrics(
            HttpServletRequest request,
            HttpServletResponse response,
            long startedAt
    ) {
        String route = matchedRoute(request);
        String statusCode = Integer.toString(response.getStatus());
        Counter.builder("serviceops.http.requests")
                .description("Completed ServiceOps HTTP requests")
                .tags(
                        "service_name", SERVICE_NAME,
                        "method", request.getMethod(),
                        "route", route,
                        "status_code", statusCode
                )
                .register(meterRegistry)
                .increment();
        Timer.builder("serviceops.http.request.duration")
                .description("ServiceOps HTTP request duration")
                .serviceLevelObjectives(
                        Duration.ofMillis(100),
                        Duration.ofMillis(250),
                        Duration.ofMillis(500),
                        Duration.ofSeconds(1),
                        Duration.ofMillis(2500)
                )
                .tags(
                        "service_name", SERVICE_NAME,
                        "method", request.getMethod(),
                        "route", route,
                        "status_code", statusCode
                )
                .register(meterRegistry)
                .record(System.nanoTime() - startedAt, TimeUnit.NANOSECONDS);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return request.getRequestURI().startsWith("/actuator/");
    }

    private String matchedRoute(HttpServletRequest request) {
        Object pattern = request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
        return pattern == null ? "UNKNOWN" : pattern.toString();
    }
}
