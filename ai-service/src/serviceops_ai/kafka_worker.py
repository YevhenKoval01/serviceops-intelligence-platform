from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from confluent_kafka import Consumer, KafkaError, Producer
from jsonschema import Draft202012Validator, FormatChecker

from serviceops_ai.model import ModelBundle

logger = logging.getLogger(__name__)
CREATED_TOPIC = "serviceops.ticket.created.v1"
PREDICTION_TOPIC = "serviceops.ticket.prediction-completed.v1"
INVALID_TOPIC = "serviceops.ticket.invalid.v1"
MAX_PROCESS_ATTEMPTS = 3
PRODUCE_TIMEOUT_SECONDS = 10


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
        # A deterministic output id makes replayed input events idempotent downstream.
        "eventId": str(uuid5(NAMESPACE_URL, f"serviceops:prediction:{event['eventId']}")),
        "eventType": "ticket.prediction-completed",
        "eventVersion": 1,
        "occurredAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "correlationId": event["correlationId"],
        "ticketId": event["ticketId"],
        "payload": prediction.model_dump(),
    }


def create_invalid_event(raw_message: str, reason: str) -> dict[str, Any]:
    return {
        "failedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "reason": reason,
        "sourceTopic": CREATED_TOPIC,
        "originalMessage": raw_message,
    }


def publish_with_retry(
    producer: Producer,
    topic: str,
    value: str,
    *,
    key: str | None = None,
    attempts: int = MAX_PROCESS_ATTEMPTS,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        delivered = threading.Event()
        delivery_errors: list[str] = []

        def delivery_callback(
            error: Any,
            _: Any,
            errors: list[str] = delivery_errors,
            completed: threading.Event = delivered,
        ) -> None:
            if error is not None:
                errors.append(str(error))
            completed.set()

        try:
            producer.produce(
                topic,
                key=key,
                value=value,
                on_delivery=delivery_callback,
            )
            remaining = producer.flush(PRODUCE_TIMEOUT_SECONDS)
            if remaining != 0:
                raise RuntimeError(f"{remaining} Kafka message(s) remained undelivered")
            if not delivered.is_set():
                raise RuntimeError("Kafka delivery callback did not complete")
            if delivery_errors:
                raise RuntimeError(f"Kafka delivery failed: {delivery_errors[0]}")
            return
        except (BufferError, RuntimeError) as exception:
            last_error = exception
            if attempt < attempts:
                producer.poll(0)
                time.sleep(0.25 * attempt)
    raise RuntimeError(f"Kafka publication failed after {attempts} attempts") from last_error


class KafkaPredictionWorker:
    def __init__(self, model: ModelBundle, bootstrap_servers: str) -> None:
        self._model = model
        self._bootstrap_servers = bootstrap_servers
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._validator = load_created_validator()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_ready(self) -> bool:
        return self.is_running and self._ready.is_set()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop.clear()
        self._ready.clear()
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
        try:
            consumer.list_topics(timeout=10)
            self._ready.set()
            logger.info("Kafka prediction worker subscribed to %s", CREATED_TOPIC)
            while not self._stop.is_set():
                record = consumer.poll(1.0)
                if record is None:
                    continue
                if record.error():
                    if record.error().code() != KafkaError._PARTITION_EOF:
                        logger.error("Kafka consumer error: %s", record.error())
                    continue
                raw_bytes = record.value()
                raw_message = (
                    raw_bytes.decode("utf-8", errors="replace")
                    if isinstance(raw_bytes, bytes)
                    else str(raw_bytes)
                )
                try:
                    event = parse_created_event(raw_message, self._validator)
                except (json.JSONDecodeError, ValueError, KeyError) as exception:
                    invalid = create_invalid_event(raw_message, str(exception))
                    publish_with_retry(
                        producer,
                        INVALID_TOPIC,
                        json.dumps(invalid),
                    )
                    consumer.commit(record, asynchronous=False)
                    logger.warning("Sent invalid ticket event to dead-letter topic: %s", exception)
                    continue

                processing_error: Exception | None = None
                for attempt in range(1, MAX_PROCESS_ATTEMPTS + 1):
                    try:
                        prediction_event = create_prediction_event(event, self._model)
                        publish_with_retry(
                            producer,
                            PREDICTION_TOPIC,
                            json.dumps(prediction_event),
                            key=event["ticketId"],
                        )
                        processing_error = None
                        break
                    except Exception as exception:
                        processing_error = exception
                        if attempt < MAX_PROCESS_ATTEMPTS:
                            time.sleep(0.25 * attempt)

                if processing_error is None:
                    consumer.commit(record, asynchronous=False)
                    logger.info("Predicted ticket %s", event["ticketId"])
                else:
                    invalid = create_invalid_event(
                        raw_message,
                        (
                            f"Prediction failed after {MAX_PROCESS_ATTEMPTS} attempts: "
                            f"{processing_error}"
                        ),
                    )
                    publish_with_retry(
                        producer,
                        INVALID_TOPIC,
                        json.dumps(invalid),
                    )
                    consumer.commit(record, asynchronous=False)
                    logger.exception(
                        "Prediction failed for ticket %s; sent to dead-letter topic",
                        event["ticketId"],
                        exc_info=processing_error,
                    )
        except Exception:
            logger.exception("Kafka prediction worker stopped unexpectedly")
        finally:
            self._ready.clear()
            consumer.close()
            remaining = producer.flush(PRODUCE_TIMEOUT_SECONDS)
            if remaining:
                logger.error("%s Kafka message(s) remained undelivered during shutdown", remaining)
