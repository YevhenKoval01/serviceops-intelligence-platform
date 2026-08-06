#!/usr/bin/env python3
"""Validate source-controlled observability contracts without third-party packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OBSERVABILITY = ROOT / "observability"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_fragments(path: Path, fragments: set[str]) -> None:
    content = read(path)
    missing = sorted(fragment for fragment in fragments if fragment not in content)
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} is missing: {', '.join(missing)}")


def validate_compose() -> None:
    path = ROOT / "compose.observability.yaml"
    content = read(path)
    required_services = {
        "otel-collector",
        "prometheus",
        "alertmanager",
        "alert-sink",
        "telemetry-data-init",
        "tempo",
        "loki",
        "grafana",
    }
    for service in required_services:
        if f"  {service}:" not in content:
            raise AssertionError(f"Observability Compose overlay is missing {service}")
    if ":latest" in content:
        raise AssertionError("Observability images must use immutable version tags")
    require_fragments(
        path,
        {
            "OTEL_PROPAGATORS: tracecontext,baggage",
            "OTEL_TRACES_EXPORTER: otlp",
            "OTEL_METRICS_EXPORTER: none",
            "OTEL_LOGS_EXPORTER: otlp",
            "127.0.0.1:${GRAFANA_PORT:-3001}:3000",
        },
    )


def validate_collector() -> None:
    require_fragments(
        OBSERVABILITY / "otel-collector.yaml",
        {
            "receivers:",
            "span_metrics:",
            "otlp/tempo:",
            "otlphttp/loki:",
            "prometheus:",
            "traces:",
            "metrics:",
            "logs:",
            "aggregation_cardinality_limit: 5000",
        },
    )


def validate_alert_contract() -> None:
    rules = OBSERVABILITY / "prometheus" / "rules" / "serviceops.yml"
    require_fragments(
        rules,
        {
            "serviceops:sli_availability:ratio30d",
            "serviceops:slo_error_budget:burn_rate5m",
            "serviceops:slo_error_budget:remaining_ratio30d",
            "serviceops:slo_latency_error_budget:remaining_ratio30d",
            "ServiceOpsSLOFastBurn",
            "ServiceOpsSLOSlowBurn",
            "ServiceOpsComponentDown",
            "runbook_url:",
        },
    )
    require_fragments(
        OBSERVABILITY / "alertmanager" / "alertmanager.yml",
        {"serviceops-operations", "http://alert-sink:8081/alerts", "send_resolved: true"},
    )
    require_fragments(
        OBSERVABILITY / "prometheus" / "rule-tests.yml",
        {"ServiceOpsSLOFastBurn", "ServiceOpsComponentDown", "exp_alerts:"},
    )


def validate_grafana() -> None:
    dashboard_path = OBSERVABILITY / "grafana" / "dashboards" / "serviceops-overview.json"
    dashboard: dict[str, Any] = json.loads(read(dashboard_path))
    assert dashboard["uid"] == "serviceops-overview"
    assert dashboard["title"] == "ServiceOps / Platform Overview"
    panels = dashboard["panels"]
    assert len(panels) >= 9
    panel_types = {panel["type"] for panel in panels}
    assert {"logs", "stat", "timeseries", "traces"}.issubset(panel_types)
    panel_titles = {panel["title"] for panel in panels}
    assert {
        "API availability",
        "Error budget remaining",
        "Correlated application logs",
        "Recent distributed traces",
    }.issubset(panel_titles)
    require_fragments(
        OBSERVABILITY / "grafana" / "provisioning" / "datasources" / "datasources.yml",
        {
            "uid: serviceops-prometheus",
            "uid: serviceops-loki",
            "uid: serviceops-tempo",
            "tracesToLogsV2:",
            "tracesToMetrics:",
            "derivedFields:",
        },
    )


def main() -> None:
    validate_compose()
    validate_collector()
    validate_alert_contract()
    validate_grafana()
    print("Observability source contracts are valid.")


if __name__ == "__main__":
    main()
