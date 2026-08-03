from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

BASE_URL = os.environ["SERVICEOPS_BASE_URL"].rstrip("/")
USERNAME = os.environ.get("SERVICEOPS_OPERATOR_USERNAME", "operator")
PASSWORD = os.environ["SERVICEOPS_OPERATOR_PASSWORD"]


def request(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 30,
) -> dict[str, Any] | str:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "serviceops-cloud-smoke/1"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    http_request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(http_request, timeout=timeout) as response:
            content = response.read().decode("utf-8")
            if response.headers.get_content_type() == "application/json":
                return json.loads(content)
            return content
    except urllib.error.HTTPError as exception:
        details = exception.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{method} {path} returned HTTP {exception.code}: {details}"
        ) from exception


def wait_for_frontend() -> None:
    deadline = time.monotonic() + 600
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = request("/health")
            if response == "UP":
                return
        except (OSError, RuntimeError) as exception:
            last_error = exception
        time.sleep(10)
    raise RuntimeError("Frontend did not become healthy within 10 minutes") from last_error


def main() -> None:
    wait_for_frontend()
    login = request(
        "/api/auth/login",
        method="POST",
        payload={"username": USERNAME, "password": PASSWORD},
    )
    assert isinstance(login, dict)
    token = str(login["accessToken"])

    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    ticket = request(
        "/api/tickets",
        method="POST",
        payload={
            "title": f"Azure deployment smoke test {suffix}",
            "description": "Production API requests return server errors for every customer.",
            "reportedPriority": "HIGH",
        },
        token=token,
    )
    assert isinstance(ticket, dict)
    ticket_id = str(ticket["id"])

    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        current = request(f"/api/tickets/{ticket_id}", token=token)
        assert isinstance(current, dict)
        if current.get("predictedCategory") and current.get("predictedPriority"):
            print(
                "Cloud smoke test passed: "
                f"ticket {ticket_id} classified as {current['predictedCategory']} / "
                f"{current['predictedPriority']}"
            )
            return
        time.sleep(5)
    raise RuntimeError(f"Ticket {ticket_id} was not classified within 5 minutes")


if __name__ == "__main__":
    main()
