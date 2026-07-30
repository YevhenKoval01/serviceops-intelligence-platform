import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from serviceops_ai.kafka_worker import parse_created_event


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
