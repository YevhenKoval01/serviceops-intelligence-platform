#!/usr/bin/env python3
"""Exercise the public ServiceOps flow using only the Python standard library."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

BACKEND = os.getenv("SERVICEOPS_BACKEND_URL", "http://localhost:8080").rstrip("/")
AI_SERVICE = os.getenv("SERVICEOPS_AI_URL", "http://localhost:8000").rstrip("/")
FRONTEND = os.getenv("SERVICEOPS_FRONTEND_URL", "http://localhost:3000").rstrip("/")


def request(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 5,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    call = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(call, timeout=timeout) as response:
        content = response.read()
        return json.loads(content) if content else None


def wait_for(url: str, timeout_seconds: int = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for {url}")


def assert_problem_details() -> None:
    try:
        request(
            f"{BACKEND}/api/tickets",
            method="POST",
            payload={"title": "bad", "description": "short"},
        )
    except urllib.error.HTTPError as error:
        problem = json.loads(error.read())
        assert error.code == 400
        assert problem["title"] == "Validation failed"
        assert problem["status"] == 400
        assert set(problem["errors"]) == {"title", "description"}
        assert error.headers.get_content_type() == "application/problem+json"
        return
    raise AssertionError("Invalid ticket request unexpectedly succeeded")


def main() -> int:
    print("Waiting for frontend, backend, and AI service...")
    wait_for(f"{FRONTEND}/health")
    wait_for(f"{BACKEND}/actuator/health")
    wait_for(f"{AI_SERVICE}/health")
    backend_health = request(f"{BACKEND}/actuator/health")
    ai_health = request(f"{AI_SERVICE}/health")
    assert backend_health["status"] == "UP"
    assert ai_health == {
        "status": "UP",
        "modelLoaded": True,
        "kafkaWorkerRunning": True,
    }
    with urllib.request.urlopen(FRONTEND, timeout=5) as response:
        frontend_html = response.read().decode("utf-8")
    assert "ServiceOps Intelligence" in frontend_html
    print("All service health checks passed.")

    assert_problem_details()
    summary_before = request(f"{BACKEND}/api/summary")

    ticket = request(
        f"{BACKEND}/api/tickets",
        method="POST",
        payload={
            "title": "Production API unavailable",
            "description": (
                "Every customer API request returns a server error and order processing is blocked."
            ),
            "reportedPriority": "HIGH",
        },
    )
    ticket_id = ticket["id"]
    assert ticket["status"] == "OPEN"
    assert ticket["predictedCategory"] is None
    print(f"Created ticket {ticket_id}; waiting for Kafka prediction...")

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        ticket = request(f"{BACKEND}/api/tickets/{ticket_id}")
        if (
            ticket["predictedCategory"]
            and ticket["predictedPriority"]
            and ticket["predictionConfidence"] is not None
        ):
            break
        time.sleep(1)
    else:
        raise TimeoutError("Prediction was not stored within 90 seconds")

    assert ticket["modelVersion"] == "baseline-1"
    assert 0 <= float(ticket["predictionConfidence"]) <= 1
    tickets = request(f"{BACKEND}/api/tickets")
    assert any(item["id"] == ticket_id for item in tickets)
    print(
        "Prediction stored: "
        f"{ticket['predictedCategory']} / {ticket['predictedPriority']} "
        f"({float(ticket['predictionConfidence']):.1%})"
    )

    updated = request(
        f"{BACKEND}/api/tickets/{ticket_id}/status",
        method="PATCH",
        payload={"status": "IN_PROGRESS"},
    )
    assert updated["status"] == "IN_PROGRESS"
    persisted = request(f"{BACKEND}/api/tickets/{ticket_id}")
    assert persisted["id"] == ticket_id
    assert persisted["status"] == "IN_PROGRESS"
    assert persisted["predictedCategory"] == ticket["predictedCategory"]
    summary_after = request(f"{BACKEND}/api/summary")
    assert summary_after["total"] == summary_before["total"] + 1
    assert summary_after["inProgress"] >= summary_before["inProgress"] + 1
    print("Status updated and ticket remains readable.")
    print(
        json.dumps(
            {
                "ticketId": ticket_id,
                "prediction": ticket["predictedCategory"],
                "priority": ticket["predictedPriority"],
                "confidence": ticket["predictionConfidence"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exception:
        print(f"Smoke test failed: {exception}", file=sys.stderr)
        raise
