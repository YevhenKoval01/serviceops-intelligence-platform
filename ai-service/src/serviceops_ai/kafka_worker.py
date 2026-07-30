from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from confluent_kafka import Consumer, KafkaError, Producer
from jsonschema import Draft202012Validator, FormatChecker

from serviceops_ai.model import ModelBundle

logger = logging.getLogger(__name__)
CREATED_TOPIC = "serviceops.ticket.created.v1"
PREDICTION_TOPIC = "serviceops.ticket.prediction-completed.v1"
INVALID_TOPIC = "serviceops.ticket.invalid.v1"


def contract_path() -> Path:
    configured = os.getenv("CONTRACTS_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "contracts"


def load_created_validator() -> Draft202012Validator:
    schema = json.loads((contract_path() / "ticket-created-v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def parse_created_event(message: str, validator: Draft202012Validator) -> dict[str, Any]:
    event = json.loads(message)
    errors = sorted(validator.iter_errors(event), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ValueError(f"Ticket event failed schema validation: {details}")
    return event


def create_prediction_event(event: dict[str, Any], model: ModelBundle) -> dict[str, Any]:
    prediction = model.predict(
        title=event["payload"]["title"],
        description=event["payload"]["description"],
    )
    return {
        "eventId": str(uuid4()),
        "eventType": "ticket.prediction-completed",
        "eventVersion": 1,
        "occurredAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "correlationId": event["correlationId"],
        "ticketId": event["ticketId"],
        "payload": prediction.model_dump(),
    }


class KafkaPredictionWorker:
    def __init__(self, model: ModelBundle, bootstrap_servers: str) -> None:
        self._model = model
        self._bootstrap_servers = bootstrap_servers
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._validator = load_created_validator()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="ticket-prediction-consumer",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _run(self) -> None:
        consumer = Consumer(
            {
                "bootstrap.servers": self._bootstrap_servers,
                "group.id": "serviceops-ai-v1",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        producer = Producer(
            {
                "bootstrap.servers": self._bootstrap_servers,
                "enable.idempotence": True,
            }
        )
        consumer.subscribe([CREATED_TOPIC])
        logger.info("Kafka prediction worker subscribed to %s", CREATED_TOPIC)
        try:
            while not self._stop.is_set():
                record = consumer.poll(1.0)
                if record is None:
                    continue
                if record.error():
                    if record.error().code() != KafkaError._PARTITION_EOF:
                        logger.error("Kafka consumer error: %s", record.error())
                    continue
                raw_message = record.value().decode("utf-8")
                try:
                    event = parse_created_event(raw_message, self._validator)
                    prediction_event = create_prediction_event(event, self._model)
                    producer.produce(
                        PREDICTION_TOPIC,
                        key=event["ticketId"],
                        value=json.dumps(prediction_event),
                    )
                    producer.flush(10)
                    consumer.commit(record, asynchronous=False)
                    logger.info("Predicted ticket %s", event["ticketId"])
                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    ValueError,
                    KeyError,
                ) as exception:
                    invalid = {
                        "failedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                        "reason": str(exception),
                        "sourceTopic": CREATED_TOPIC,
                        "originalMessage": raw_message,
                    }
                    producer.produce(INVALID_TOPIC, value=json.dumps(invalid))
                    producer.flush(10)
                    consumer.commit(record, asynchronous=False)
                    logger.warning("Sent invalid ticket event to dead-letter topic: %s", exception)
        finally:
            consumer.close()
            producer.flush(10)
