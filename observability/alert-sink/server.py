from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any

MAX_PAYLOAD_BYTES = 1_048_576
received_alerts: list[dict[str, Any]] = []
alerts_lock = Lock()


class AlertHandler(BaseHTTPRequestHandler):
    server_version = "ServiceOpsAlertSink/1.0"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "UP"})
            return
        if self.path == "/alerts":
            with alerts_lock:
                alerts = list(received_alerts)
            self._json(HTTPStatus.OK, {"alerts": alerts})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not-found"})

    def do_POST(self) -> None:
        if self.path != "/alerts":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not-found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid-content-length"})
            return
        if content_length <= 0 or content_length > MAX_PAYLOAD_BYTES:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid-payload-size"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid-json"})
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid-alertmanager-payload"})
            return
        record = {
            "receivedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "status": payload.get("status"),
            "alerts": payload["alerts"],
        }
        with alerts_lock:
            received_alerts.append(record)
            del received_alerts[:-100]
        self._json(HTTPStatus.OK, {"accepted": True})

    def log_message(self, format_: str, *args: Any) -> None:
        return

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8081), AlertHandler).serve_forever()
