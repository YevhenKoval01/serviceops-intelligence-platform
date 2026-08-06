# Observability response runbook

This runbook is the operational contract for ServiceOps alerts. The responder owns the
incident until it is explicitly handed over, documents timestamps in UTC, and never copies
ticket descriptions, bearer tokens, credentials, or knowledge questions into incident chat.

## Initial response

1. Acknowledge a critical alert within five minutes or a warning within fifteen minutes.
2. Confirm the alert in Alertmanager and record its `startsAt`, service, severity, and SLO.
3. Open the `ServiceOps / Platform Overview` dashboard with the alert time range preserved.
4. Determine customer impact using request rate, `5xx` ratio, p95 latency, and ticket flow.
5. Open a representative Tempo trace and follow its trace-to-logs link. Prefer trace ID,
   service, route template, and status filters; do not search by customer payload.
6. Assign an incident lead and communication owner for a critical alert.

## Component down

`ServiceOpsComponentDown` means Prometheus could not scrape Spring or FastAPI for 30 seconds.

1. Confirm `up{job="<job>"}` is zero and distinguish a scrape failure from a dead process.
2. Inspect container state and recent logs. For the backend, check PostgreSQL and Kafka health;
   for FastAPI, check model, knowledge index, and Kafka-worker readiness.
3. If only telemetry is unreachable but the public health endpoint works, follow
   [Telemetry pipeline down](#telemetry-pipeline-down).
4. Restart a failed application only after capturing its termination reason. The durable
   outbox and idempotent consumers make process restart safe; do not delete volumes.
5. Confirm health, `up == 1`, fresh request metrics, new traces, and a resolved Alertmanager
   notification before closing the incident.

## Availability SLO burn

`ServiceOpsSLOFastBurn` fires above 14.4x for two minutes. `ServiceOpsSLOSlowBurn` fires above
6x for fifteen minutes. Both protect the 99.5% rolling 30-day availability objective.

1. Compare error rate by service, route template, and status code. Do not add raw URL IDs to
   metric labels.
2. Use an errored trace to identify the failing dependency or message operation, then use its
   trace ID to inspect correlated logs in Loki.
3. Check PostgreSQL pool health, Kafka broker health, outbox retry logs, AI readiness, and
   recent deployment/configuration changes.
4. Roll back or disable the smallest responsible change when a known safe action exists.
5. If the remaining 30-day budget reaches zero, freeze non-remediation releases until the
   service owner accepts the risk or the budget recovers.

## High latency

`ServiceOpsHighLatency` means five-minute p95 request latency exceeded one second for ten
minutes. The rolling target is that at least 95% of requests complete within one second.

1. Compare route templates and services, then inspect the slowest representative traces.
2. Separate database, Kafka acknowledgement, authentication, model, retrieval, and Nginx
   proxy time using child spans.
3. Check request concurrency and resource saturation before increasing capacity or timeouts.
4. Treat a timeout increase as a temporary mitigation, not a root-cause fix.
5. Confirm p95 recovery and that the 30-day latency budget is no longer decreasing.

## Telemetry pipeline down

`ServiceOpsTelemetryPipelineDown` means the Collector, Loki, or Tempo metrics endpoint is
unreachable for two minutes.

1. Check Collector health and logs for rejected data, queue pressure, or exporter failures.
2. Check Loki `/ready`, Tempo `/ready`, and their volume availability independently.
3. Preserve application availability first. Telemetry exporter failures must not block an
   API response, outbox publication, or prediction.
4. Restore the failed telemetry component, then require fresh metrics, one log stream per
   application, and one searchable trace per application.
5. Record any observability blind window in the incident timeline.

## Resolution and learning

An incident is resolved only after the customer-facing symptom is gone, the alert is
resolved, telemetry is current, and the incident lead records the mitigation. Within two
business days for a critical incident, capture impact, timeline, contributing conditions,
root cause, detection quality, remediation owner, due date, and a regression test. Avoid
blame and distinguish the triggering change from the system conditions that allowed impact.

## Tested drill

The deterministic local drill validates detection, routing, notification, recovery, and
resolution without deleting data:

```bash
python scripts/observability_smoke_test.py \
  --exercise-alert \
  --project-name serviceops-observability-verify
```

The drill stops only `ai-service`, waits for the real Prometheus rule and Alertmanager route,
checks the webhook payload, starts the service, and requires a resolved webhook event. The
CI rule test separately feeds fixed counter series into `promtool` and verifies both the SLO
fast-burn and component-down alert labels and runbook annotations.
