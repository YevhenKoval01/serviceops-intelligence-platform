package io.github.yevhenkoval.serviceops.config;

import static org.assertj.core.api.Assertions.assertThat;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.HandlerMapping;

class HttpMetricsFilterTest {

    @Test
    void recordsBoundedRouteStatusAndDurationMetrics() throws Exception {
        var registry = new SimpleMeterRegistry();
        var filter = new HttpMetricsFilter(Optional.of(registry));
        var request = new MockHttpServletRequest("GET", "/api/tickets/123");
        var response = new MockHttpServletResponse();

        filter.doFilter(request, response, (currentRequest, currentResponse) -> {
            currentRequest.setAttribute(
                    HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE,
                    "/api/tickets/{id}"
            );
            ((MockHttpServletResponse) currentResponse).setStatus(200);
        });

        assertThat(registry.get("serviceops.http.requests").counter().count()).isEqualTo(1);
        assertThat(registry.get("serviceops.http.request.duration").timer().count()).isEqualTo(1);
        assertThat(registry.get("serviceops.http.requests").counter().getId().getTag("route"))
                .isEqualTo("/api/tickets/{id}");
    }

    @Test
    void excludesActuatorEndpointsFromApplicationSliMetrics() throws Exception {
        var registry = new SimpleMeterRegistry();
        var filter = new HttpMetricsFilter(Optional.of(registry));
        var request = new MockHttpServletRequest("GET", "/actuator/prometheus");

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> { });

        assertThat(registry.find("serviceops.http.requests").counter()).isNull();
    }
}
