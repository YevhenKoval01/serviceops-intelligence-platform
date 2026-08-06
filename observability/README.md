# Observability

The opt-in observability overlay turns the instrumented ServiceOps applications into a
complete local telemetry system without increasing the normal five-service footprint.
Spring Boot uses the pinned OpenTelemetry Java agent; FastAPI uses the pinned Python distro
and automatic FastAPI, logging, and Confluent Kafka instrumentation. Both expose bounded
Prometheus SLI metrics and export OTLP/HTTP traces and logs with W3C
`tracecontext`/`baggage` propagation. The Collector derives a second RED-metrics view from
those spans.

| Component | Version | Responsibility |
| --- | --- | --- |
| OpenTelemetry Collector Contrib | 0.152.0 | OTLP ingress, bounded batching, span-derived RED metrics, and signal routing |
| Prometheus | 3.13.0 | Application/collector metrics, 30-day SLO records, and checked alert rules |
| Alertmanager | 0.32.1 | Alert grouping, lifecycle, and webhook notification delivery |
| Grafana | 13.1.0 | Provisioned metrics, logs, and traces data sources plus the platform dashboard |
| Loki | 3.7.2 | OTLP application logs and trace-linked log exploration |
| Tempo | 2.10.5 | OTLP distributed traces and TraceQL search |

All host-facing telemetry ports bind to `127.0.0.1`. The default receiver is a deliberately
small in-memory webhook sink that proves firing and resolved delivery without contacting a
person. Replace `observability/alertmanager/alertmanager.yml` with an approved receiver for a
real environment.

## Start and inspect

The overlay needs Docker Compose v2 and approximately 6 GB of available memory for the full
application and telemetry control plane:

```bash
docker compose \
  -f compose.yaml \
  -f compose.observability.yaml \
  up --build --detach --wait
python scripts/smoke_test.py
python scripts/observability_smoke_test.py
```

Open the provisioned `ServiceOps / Platform Overview` dashboard at
<http://localhost:3001/d/serviceops-overview>. The local credentials are
`admin` / `serviceops_observe_2026`; override `GRAFANA_ADMIN_PASSWORD` outside an isolated
machine. Other diagnostic interfaces are local-only by default:

- Prometheus and rule state: <http://localhost:9090>
- Alertmanager: <http://localhost:9093>
- Tempo API: <http://localhost:3200>
- Loki API: <http://localhost:3100>
- Test notification receiver: <http://localhost:18081/alerts>

Grafana provisions Prometheus, Loki, and Tempo as code. Trace views link to logs by
`service.name` and trace ID; Loki log details link back to Tempo; Tempo spans link to the
uniform ServiceOps HTTP metrics. No ticket title, description, knowledge question, token,
or credential is added to a metric label or custom span attribute. Kafka consumer processing
uses the OpenTelemetry messaging semantic convention's span link back to the producer trace;
the runtime smoke test verifies that link resolves to the Java service.

## Objectives and alert drill

The checked rules define two rolling 30-day objectives for `serviceops-backend` and
`serviceops-ai-service`:

- Availability: at least 99.5% of completed requests do not return `5xx`. The 0.5% budget is
  3 hours 36 minutes of equivalent unavailability in 30 days.
- Latency: at least 95% of requests complete within one second. The allowed slow-request
  budget is 5% in 30 days.

Fast (14.4x) and slow (6x) availability-budget alerts, p95 latency, application-down, and
telemetry-pipeline alerts link to the operational runbook. Rule expressions and expected
alerts are tested with `promtool`. The optional drill stops only the AI container, waits for
Prometheus to fire `ServiceOpsComponentDown`, proves Alertmanager and webhook receipt, then
starts the service and requires a resolved notification:

```bash
python scripts/observability_smoke_test.py \
  --exercise-alert \
  --project-name serviceops-observability-verify
```

Use the same project name that was passed to `docker compose -p`. The script restores the
AI service in a `finally` block if a verification assertion fails.

## Configuration validation

```bash
python scripts/validate_observability.py
docker compose -f compose.yaml -f compose.observability.yaml config --quiet
docker run --rm -v "$PWD/observability/prometheus:/etc/prometheus:ro" \
  --entrypoint /bin/promtool prom/prometheus:v3.13.0 \
  test rules /etc/prometheus/rule-tests.yml
```

CI additionally validates the Prometheus, Alertmanager, Collector, and Loki configurations
with their pinned binaries and parses the dashboard and alert receiver.

## Retention and production use

The overlay is a single-node validation topology. Prometheus retains metrics for 30 days;
the local Loki and Tempo stores retain 24 hours and use named volumes. It is not an HA or
capacity-tested telemetry backend. A production deployment should use protected ingress,
durable replicated storage, approved retention, external notification routing, backups, and
access control appropriate to its environment.

The application images are portable. Azure Terraform keeps telemetry disabled by default,
but setting `otel_exporter_otlp_endpoint` to an HTTPS OTLP endpoint enables all three signals
for Spring and FastAPI. Optional exporter headers are injected as Container Apps secrets,
and the default cloud sampling ratio is 10%.
