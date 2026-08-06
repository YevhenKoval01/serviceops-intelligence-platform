#!/usr/bin/env python3
"""Verify metrics, logs, traces, dashboards, SLOs, and the alert delivery path."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROMETHEUS = os.getenv("SERVICEOPS_PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
ALERTMANAGER = os.getenv("SERVICEOPS_ALERTMANAGER_URL", "http://localhost:9093").rstrip("/")
ALERT_SINK = os.getenv("SERVICEOPS_ALERT_SINK_URL", "http://localhost:18081").rstrip("/")
LOKI = os.getenv("SERVICEOPS_LOKI_URL", "http://localhost:3100").rstrip("/")
TEMPO = os.getenv("SERVICEOPS_TEMPO_URL", "http://localhost:3200").rstrip("/")
GRAFANA = os.getenv("SERVICEOPS_GRAFANA_URL", "http://localhost:3001").rstrip("/")
AI_SERVICE = os.getenv("SERVICEOPS_AI_URL", "http://localhost:8000").rstrip("/")
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "serviceops_observe_2026")


def request_json(url: str, *, basic_auth: tuple[str, str] | None = None) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "serviceops-observability-smoke/1"}
    if basic_auth:
        encoded = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        content = response.read()
        return json.loads(content) if content else None


def wait_until(
    description: str,
    assertion: Callable[[], Any],
    *,
    timeout_seconds: int = 180,
    interval_seconds: float = 3,
) -> Any:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = assertion()
            if result:
                return result
        except (AssertionError, KeyError, OSError, TimeoutError, urllib.error.URLError) as error:
            last_error = error
        time.sleep(interval_seconds)
    raise TimeoutError(f"Timed out waiting for {description}") from last_error


def wait_ready(url: str) -> bool:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status == 200


def prometheus_query(expression: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"query": expression})
    payload = request_json(f"{PROMETHEUS}/api/v1/query?{query}")
    assert payload["status"] == "success"
    return payload["data"]["result"]


def metric_exists(expression: str) -> list[dict[str, Any]]:
    result = prometheus_query(expression)
    assert result
    return result


def verify_control_plane() -> None:
    endpoints = {
        "Prometheus": f"{PROMETHEUS}/-/ready",
        "Alertmanager": f"{ALERTMANAGER}/-/ready",
        "alert receiver": f"{ALERT_SINK}/health",
        "Loki": f"{LOKI}/ready",
        "Tempo": f"{TEMPO}/ready",
        "Grafana": f"{GRAFANA}/api/health",
    }
    for name, url in endpoints.items():
        wait_until(f"{name} readiness", lambda current_url=url: wait_ready(current_url))


def verify_metrics_and_slos() -> None:
    for job in ("serviceops-backend", "serviceops-ai-service", "serviceops-otel-collector"):
        metric_exists(f'up{{job="{job}"}} == 1')
    for service in ("serviceops-backend", "serviceops-ai-service"):
        wait_until(
            f"HTTP SLI metrics for {service}",
            lambda current_service=service: metric_exists(
                f'serviceops_http_requests_total{{service_name="{current_service}"}}'
            ),
        )
        wait_until(
            f"trace-derived request metrics for {service}",
            lambda current_service=service: metric_exists(
                '{__name__=~"serviceops_spanmetrics_calls(_total)?",'
                f'service_name="{current_service}"}}'
            ),
        )

    rules = request_json(f"{PROMETHEUS}/api/v1/rules")
    assert rules["status"] == "success"
    rule_names = {
        rule["name"]
        for group in rules["data"]["groups"]
        for rule in group["rules"]
    }
    assert {
        "serviceops:sli_availability:ratio5m",
        "serviceops:slo_error_budget:burn_rate5m",
        "ServiceOpsSLOFastBurn",
        "ServiceOpsComponentDown",
    }.issubset(rule_names)


def tempo_traceql(traceql: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"q": traceql, "limit": 20})
    payload = request_json(f"{TEMPO}/api/search?{query}")
    return payload.get("traces", [])


def tempo_search(service_name: str) -> list[dict[str, Any]]:
    return tempo_traceql(f'{{ resource.service.name = "{service_name}" }}')


def trace_service_names(trace: dict[str, Any]) -> set[str]:
    services: set[str] = set()
    for batch in trace.get("batches", []):
        for attribute in batch.get("resource", {}).get("attributes", []):
            if attribute.get("key") == "service.name":
                services.add(attribute.get("value", {}).get("stringValue", ""))
    return services


def linked_backend_trace() -> bool:
    consumer_traces = tempo_traceql(
        '{ resource.service.name = "serviceops-ai-service" '
        '&& name = "serviceops.ticket.created.v1 process" }'
    )
    for summary in consumer_traces:
        trace = request_json(f"{TEMPO}/api/traces/{summary['traceID']}")
        for batch in trace.get("batches", []):
            for scope in batch.get("scopeSpans", []):
                for span in scope.get("spans", []):
                    for link in span.get("links", []):
                        linked_trace_id = base64.b64decode(link["traceId"]).hex()
                        linked_trace = request_json(f"{TEMPO}/api/traces/{linked_trace_id}")
                        if "serviceops-backend" in trace_service_names(linked_trace):
                            return True
    return False


def loki_query(service_name: str) -> list[dict[str, Any]]:
    now_ns = time.time_ns()
    query = urllib.parse.urlencode(
        {
            "query": f'{{service_name="{service_name}"}}',
            "start": now_ns - 30 * 60 * 1_000_000_000,
            "end": now_ns,
            "limit": 100,
        }
    )
    payload = request_json(f"{LOKI}/loki/api/v1/query_range?{query}")
    assert payload["status"] == "success"
    return payload["data"]["result"]


def verify_logs_and_traces() -> None:
    for service in ("serviceops-backend", "serviceops-ai-service"):
        wait_until(
            f"Tempo traces for {service}",
            lambda current_service=service: tempo_search(current_service),
        )
        wait_until(
            f"Loki logs for {service}",
            lambda current_service=service: loki_query(current_service),
        )
    wait_until("Kafka producer-to-consumer trace link", linked_backend_trace)


def verify_grafana() -> None:
    auth = (GRAFANA_USER, GRAFANA_PASSWORD)
    dashboards = request_json(
        f"{GRAFANA}/api/search?{urllib.parse.urlencode({'query': 'ServiceOps'})}",
        basic_auth=auth,
    )
    assert any(item.get("uid") == "serviceops-overview" for item in dashboards)
    for uid in ("serviceops-prometheus", "serviceops-loki", "serviceops-tempo"):
        datasource = request_json(f"{GRAFANA}/api/datasources/uid/{uid}", basic_auth=auth)
        assert datasource["uid"] == uid


def compose(project_name: str, action: str) -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            project_name,
            "-f",
            "compose.yaml",
            "-f",
            "compose.observability.yaml",
            action,
            "ai-service",
        ],
        cwd=ROOT,
        check=True,
    )


def firing_component_alert() -> list[dict[str, Any]]:
    query = "active=true&silenced=false&inhibited=false"
    alerts = request_json(f"{ALERTMANAGER}/api/v2/alerts?{query}")
    return [
        alert
        for alert in alerts
        if alert.get("labels", {}).get("alertname") == "ServiceOpsComponentDown"
        and alert.get("labels", {}).get("job") == "serviceops-ai-service"
    ]


def delivered_alert(status: str) -> list[dict[str, Any]]:
    records = request_json(f"{ALERT_SINK}/alerts")["alerts"]
    matching: list[dict[str, Any]] = []
    for record in records:
        for alert in record.get("alerts", []):
            labels = alert.get("labels", {})
            if (
                labels.get("alertname") == "ServiceOpsComponentDown"
                and labels.get("job") == "serviceops-ai-service"
                and alert.get("status") == status
            ):
                matching.append(alert)
    return matching


def exercise_alert_path(project_name: str) -> None:
    compose(project_name, "stop")
    try:
        wait_until(
            "Prometheus component-down alert",
            lambda: metric_exists(
                'ALERTS{alertname="ServiceOpsComponentDown",job="serviceops-ai-service",'
                'alertstate="firing"}'
            ),
            timeout_seconds=120,
        )
        wait_until("Alertmanager receipt", firing_component_alert, timeout_seconds=90)
        wait_until(
            "webhook notification delivery",
            lambda: delivered_alert("firing"),
            timeout_seconds=90,
        )
    finally:
        compose(project_name, "start")
        wait_until("AI service recovery", lambda: wait_ready(f"{AI_SERVICE}/health"))
    wait_until(
        "resolved webhook notification",
        lambda: delivered_alert("resolved"),
        timeout_seconds=120,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise-alert", action="store_true")
    parser.add_argument("--project-name", default="serviceops-observability-verify")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verify_control_plane()
    verify_metrics_and_slos()
    verify_logs_and_traces()
    verify_grafana()
    if args.exercise_alert:
        exercise_alert_path(args.project_name)
    verified_alerts = "alert delivery and recovery" if args.exercise_alert else "alert rules"
    print(
        "Observability smoke test passed: metrics, SLOs, logs, linked Kafka traces, "
        f"dashboards, and {verified_alerts}."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Observability smoke test failed: {error}", file=sys.stderr)
        raise
