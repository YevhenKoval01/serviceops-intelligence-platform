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
OPERATOR_USERNAME = os.getenv("SERVICEOPS_AUTH_OPERATOR_USERNAME", "operator")
OPERATOR_PASSWORD = os.getenv("SERVICEOPS_AUTH_OPERATOR_PASSWORD", "operator_dev_2026")
VIEWER_USERNAME = os.getenv("SERVICEOPS_AUTH_VIEWER_USERNAME", "viewer")
VIEWER_PASSWORD = os.getenv("SERVICEOPS_AUTH_VIEWER_PASSWORD", "viewer_dev_2026")


def request(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 5,
    headers: dict[str, str] | None = None,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    call = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=request_headers,
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


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(username: str, password: str) -> dict[str, Any]:
    response = request(
        f"{BACKEND}/api/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    assert response["tokenType"] == "Bearer"
    assert response["expiresIn"] > 0
    assert response["user"]["username"] == username
    return response


def assert_unauthenticated_request_is_rejected() -> None:
    try:
        request(f"{BACKEND}/api/tickets")
    except urllib.error.HTTPError as error:
        problem = json.loads(error.read())
        assert error.code == 401
        assert problem["type"].endswith("/authentication-required")
        assert error.headers.get_content_type() == "application/problem+json"
        return
    raise AssertionError("Anonymous ticket request unexpectedly succeeded")


def assert_viewer_cannot_create_ticket(headers: dict[str, str]) -> None:
    try:
        request(
            f"{BACKEND}/api/tickets",
            method="POST",
            payload={
                "title": "Viewer mutation attempt",
                "description": "A read-only account must not create a ticket.",
            },
            headers=headers,
        )
    except urllib.error.HTTPError as error:
        problem = json.loads(error.read())
        assert error.code == 403
        assert problem["type"].endswith("/access-denied")
        return
    raise AssertionError("Viewer ticket mutation unexpectedly succeeded")


def assert_ai_role_boundary(viewer_headers: dict[str, str]) -> None:
    try:
        request(f"{AI_SERVICE}/model-info")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError("Anonymous model metadata request unexpectedly succeeded")

    try:
        request(
            f"{AI_SERVICE}/predict",
            method="POST",
            payload={
                "title": "Viewer direct prediction",
                "description": "A read-only account must not run direct prediction.",
            },
            headers=viewer_headers,
        )
    except urllib.error.HTTPError as error:
        assert error.code == 403
        return
    raise AssertionError("Viewer direct prediction unexpectedly succeeded")


def assert_problem_details(headers: dict[str, str]) -> None:
    try:
        request(
            f"{BACKEND}/api/tickets",
            method="POST",
            payload={"title": "bad", "description": "short"},
            headers=headers,
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
        "knowledgeBaseReady": True,
        "knowledgeDocuments": 6,
        "knowledgeChunks": 18,
    }
    with urllib.request.urlopen(FRONTEND, timeout=5) as response:
        frontend_html = response.read().decode("utf-8")
    assert "ServiceOps Intelligence" in frontend_html
    print("All service health checks passed.")

    assert_unauthenticated_request_is_rejected()
    operator_session = login(OPERATOR_USERNAME, OPERATOR_PASSWORD)
    viewer_session = login(VIEWER_USERNAME, VIEWER_PASSWORD)
    assert operator_session["user"]["role"] == "OPERATOR"
    assert viewer_session["user"]["role"] == "VIEWER"
    operator_headers = bearer(operator_session["accessToken"])
    viewer_headers = bearer(viewer_session["accessToken"])
    current_user = request(f"{BACKEND}/api/auth/me", headers=operator_headers)
    assert current_user == operator_session["user"]
    request(f"{BACKEND}/api/tickets", headers=viewer_headers)
    assert_viewer_cannot_create_ticket(viewer_headers)
    assert_ai_role_boundary(viewer_headers)
    model_info = request(f"{AI_SERVICE}/model-info", headers=viewer_headers)
    assert model_info["modelVersion"] == "baseline-2"
    assert model_info["trainingRows"] == 1_000
    print("Authentication and role-based access checks passed.")

    knowledge_answer = request(
        f"{FRONTEND}/assistant/ask",
        method="POST",
        payload={"question": "How should I investigate repeated HTTP 500 API errors?"},
        headers=viewer_headers,
    )
    assert knowledge_answer["grounded"] is True
    assert knowledge_answer["citations"]
    assert knowledge_answer["citations"][0]["documentId"] == "technical-api-errors"
    assert "[1]" in knowledge_answer["answer"]
    unsupported_answer = request(
        f"{FRONTEND}/assistant/ask",
        method="POST",
        payload={"question": "What is served in the office cafeteria today?"},
        headers=viewer_headers,
    )
    assert unsupported_answer["grounded"] is False
    assert unsupported_answer["citations"] == []
    print("Citation-grounded retrieval and unsupported-question abstention passed.")

    assert_problem_details(operator_headers)
    summary_before = request(f"{BACKEND}/api/summary", headers=operator_headers)

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
        headers=operator_headers,
    )
    ticket_id = ticket["id"]
    assert ticket["status"] == "OPEN"
    assert ticket["predictedCategory"] is None
    print(f"Created ticket {ticket_id}; waiting for Kafka prediction...")

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        ticket = request(f"{BACKEND}/api/tickets/{ticket_id}", headers=operator_headers)
        if (
            ticket["predictedCategory"]
            and ticket["predictedPriority"]
            and ticket["predictionConfidence"] is not None
        ):
            break
        time.sleep(1)
    else:
        raise TimeoutError("Prediction was not stored within 90 seconds")

    assert ticket["modelVersion"] == "baseline-2"
    assert 0 <= float(ticket["predictionConfidence"]) <= 1
    tickets = request(f"{BACKEND}/api/tickets", headers=operator_headers)
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
        headers=operator_headers,
    )
    assert updated["status"] == "IN_PROGRESS"
    persisted = request(f"{BACKEND}/api/tickets/{ticket_id}", headers=operator_headers)
    assert persisted["id"] == ticket_id
    assert persisted["status"] == "IN_PROGRESS"
    assert persisted["predictedCategory"] == ticket["predictedCategory"]
    summary_after = request(f"{BACKEND}/api/summary", headers=operator_headers)
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
