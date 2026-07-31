import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from serviceops_ai.kafka_worker import (
    create_invalid_event,
    create_prediction_event,
    parse_created_event,
    publish_with_retry,
)
from serviceops_ai.model import train_model

DATASET = Path(__file__).parents[1] / "data" / "training_tickets.csv"


def validator() -> Draft202012Validator:
    schema_path = Path(__file__).parents[2] / "contracts" / "ticket-created-v1.json"
    return Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )


def test_invalid_kafka_event_is_rejected() -> None:
    invalid = json.dumps(
        {
            "eventId": "not-a-uuid",
            "eventType": "ticket.created",
            "eventVersion": 1,
            "payload": {},
        }
    )

    with pytest.raises(ValueError, match="schema validation"):
        parse_created_event(invalid, validator())


def valid_event() -> dict[str, Any]:
    return {
        "eventId": "08e805d0-bba6-4c70-abce-5420ae697732",
        "eventType": "ticket.created",
        "eventVersion": 1,
        "occurredAt": "2026-07-30T10:00:00Z",
        "correlationId": "08e805d0-bba6-4c70-abce-5420ae697732",
        "ticketId": "23dc7d80-d74f-4d56-8c8c-caf97dc9ed23",
        "payload": {
            "title": "Production API unavailable",
            "description": "Every customer API request returns a server error.",
            "reportedPriority": "HIGH",
        },
    }


def test_prediction_event_id_is_stable_for_replayed_input() -> None:
    model = train_model(DATASET)

    first = create_prediction_event(valid_event(), model)
    second = create_prediction_event(valid_event(), model)

    assert first["eventId"] == second["eventId"]
    assert first["correlationId"] == valid_event()["correlationId"]
    assert first["ticketId"] == valid_event()["ticketId"]


def test_invalid_event_contains_dead_letter_context() -> None:
    invalid = create_invalid_event("{not-json", "Invalid JSON")

    assert invalid["sourceTopic"] == "serviceops.ticket.created.v1"
    assert invalid["reason"] == "Invalid JSON"
    assert invalid["originalMessage"] == "{not-json"
    assert invalid["failedAt"].endswith("Z")


class FakeProducer:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def produce(
        self,
        topic: str,
        *,
        key: str | None,
        value: str,
        on_delivery: Any,
    ) -> None:
        self.calls += 1
        error = "broker unavailable" if self.calls <= self.failures else None
        on_delivery(error, {"topic": topic, "key": key, "value": value})

    def flush(self, _: int) -> int:
        return 0

    def poll(self, _: int) -> None:
        return None


def test_publication_uses_bounded_retries() -> None:
    producer = FakeProducer(failures=2)

    publish_with_retry(
        producer,  # type: ignore[arg-type]
        "serviceops.ticket.prediction-completed.v1",
        "{}",
        key="ticket-id",
    )

    assert producer.calls == 3


def test_publication_fails_after_retry_budget() -> None:
    producer = FakeProducer(failures=3)

    with pytest.raises(RuntimeError, match="after 3 attempts"):
        publish_with_retry(
            producer,  # type: ignore[arg-type]
            "serviceops.ticket.prediction-completed.v1",
            "{}",
        )

    assert producer.calls == 3
