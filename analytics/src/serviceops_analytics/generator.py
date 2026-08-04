from __future__ import annotations

import argparse
import hashlib
import os
import random
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

NAMESPACE = uuid.UUID("6ad9d67c-6e32-5dc3-b13d-c086f49825c9")
DEFAULT_ANCHOR = datetime(2026, 7, 31, tzinfo=UTC)
DEFAULT_EVENT_COUNT = 100_000
DEFAULT_SEED = 20_260_804

STATE_PATTERNS = (
    ("OPEN",),
    ("OPEN",),
    ("OPEN",),
    ("OPEN", "IN_PROGRESS"),
    ("OPEN", "IN_PROGRESS", "RESOLVED"),
    ("OPEN", "IN_PROGRESS", "RESOLVED"),
    ("OPEN", "IN_PROGRESS", "RESOLVED", "OPEN"),
    ("OPEN", "IN_PROGRESS", "RESOLVED", "OPEN", "RESOLVED"),
)
CATEGORIES = ("access", "hardware", "network", "software")
PRIORITIES = ("LOW", "MEDIUM", "HIGH")


@dataclass(frozen=True)
class TicketRow:
    ticket_id: uuid.UUID
    title: str
    description: str
    status: str
    reported_priority: str | None
    predicted_priority: str
    predicted_category: str
    prediction_confidence: Decimal
    model_version: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class LifecycleEventRow:
    event_id: uuid.UUID
    ticket_id: uuid.UUID
    event_type: str
    previous_status: str | None
    current_status: str
    occurred_at: datetime


@dataclass(frozen=True)
class Dataset:
    tickets: tuple[TicketRow, ...]
    events: tuple[LifecycleEventRow, ...]
    digest: str


def generate_dataset(
    event_count: int = DEFAULT_EVENT_COUNT,
    seed: int = DEFAULT_SEED,
    anchor: datetime = DEFAULT_ANCHOR,
) -> Dataset:
    if event_count < 1:
        raise ValueError("event_count must be positive")
    if anchor.tzinfo is None:
        raise ValueError("anchor must include a timezone")

    rng = random.Random(seed)
    tickets: list[TicketRow] = []
    events: list[LifecycleEventRow] = []
    remaining = event_count
    pattern_index = 0

    while remaining:
        states = STATE_PATTERNS[pattern_index % len(STATE_PATTERNS)]
        pattern_index += 1
        if len(states) > remaining:
            states = states[:remaining]
        remaining -= len(states)

        ticket_index = len(tickets)
        ticket_id = uuid.uuid5(NAMESPACE, f"{seed}:ticket:{ticket_index}")
        category = CATEGORIES[(ticket_index + rng.randrange(len(CATEGORIES))) % len(CATEGORIES)]
        priority = PRIORITIES[(ticket_index + rng.randrange(len(PRIORITIES))) % len(PRIORITIES)]
        created_at = anchor - timedelta(days=730) + timedelta(
            minutes=rng.randrange(690 * 24 * 60)
        )
        occurred_at = created_at

        for event_index, state in enumerate(states):
            if event_index:
                occurred_at += timedelta(minutes=rng.randrange(15, 721))
            previous_status = states[event_index - 1] if event_index else None
            event_type = _event_type(previous_status, state)
            events.append(
                LifecycleEventRow(
                    event_id=uuid.uuid5(
                        NAMESPACE,
                        f"{seed}:ticket:{ticket_index}:event:{event_index}",
                    ),
                    ticket_id=ticket_id,
                    event_type=event_type,
                    previous_status=previous_status,
                    current_status=state,
                    occurred_at=occurred_at,
                )
            )

        reported_priority = None if ticket_index % 7 == 0 else priority
        tickets.append(
            TicketRow(
                ticket_id=ticket_id,
                title=f"Synthetic {category} lifecycle {ticket_index + 1}",
                description=(
                    "Deterministic non-sensitive analytics fixture for service operations "
                    f"lifecycle {ticket_index + 1}."
                ),
                status=states[-1],
                reported_priority=reported_priority,
                predicted_priority=priority,
                predicted_category=category,
                prediction_confidence=Decimal(70000 + rng.randrange(29001)) / Decimal(100000),
                model_version="analytics-fixture-v1",
                created_at=created_at,
                updated_at=occurred_at,
            )
        )

    digest = _dataset_digest(tickets, events)
    return Dataset(tuple(tickets), tuple(events), digest)


def load_dataset(dataset: Dataset, database_url: str) -> tuple[int, int]:
    import psycopg

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "CREATE TEMP TABLE generated_tickets "
            "(LIKE tickets INCLUDING DEFAULTS) ON COMMIT DROP"
        )
        cursor.execute(
            "CREATE TEMP TABLE generated_lifecycle_events "
            "(LIKE ticket_lifecycle_events INCLUDING DEFAULTS) ON COMMIT DROP"
        )
        with cursor.copy(
            """
            COPY generated_tickets (
                id, title, description, status, reported_priority, predicted_priority,
                predicted_category, prediction_confidence, model_version, created_at,
                updated_at, version
            ) FROM STDIN
            """
        ) as copy:
            for ticket in dataset.tickets:
                copy.write_row(
                    (
                        ticket.ticket_id,
                        ticket.title,
                        ticket.description,
                        ticket.status,
                        ticket.reported_priority,
                        ticket.predicted_priority,
                        ticket.predicted_category,
                        ticket.prediction_confidence,
                        ticket.model_version,
                        ticket.created_at,
                        ticket.updated_at,
                        0,
                    )
                )
        with cursor.copy(
            """
            COPY generated_lifecycle_events (
                id, ticket_id, event_type, previous_status, current_status, occurred_at
            ) FROM STDIN
            """
        ) as copy:
            for event in dataset.events:
                copy.write_row(
                    (
                        event.event_id,
                        event.ticket_id,
                        event.event_type,
                        event.previous_status,
                        event.current_status,
                        event.occurred_at,
                    )
                )

        cursor.execute(
            """
            INSERT INTO tickets (
                id, title, description, status, reported_priority, predicted_priority,
                predicted_category, prediction_confidence, model_version, created_at,
                updated_at, version
            )
            SELECT
                id, title, description, status, reported_priority, predicted_priority,
                predicted_category, prediction_confidence, model_version, created_at,
                updated_at, version
            FROM generated_tickets
            ON CONFLICT (id) DO NOTHING
            """
        )
        inserted_tickets = cursor.rowcount
        cursor.execute(
            """
            INSERT INTO ticket_lifecycle_events (
                id, ticket_id, event_type, previous_status, current_status, occurred_at
            )
            SELECT id, ticket_id, event_type, previous_status, current_status, occurred_at
            FROM generated_lifecycle_events
            ON CONFLICT (id) DO NOTHING
            """
        )
        inserted_events = cursor.rowcount
    return inserted_tickets, inserted_events


def _event_type(previous_status: str | None, current_status: str) -> str:
    if previous_status is None:
        return "CREATED"
    if previous_status == "RESOLVED" and current_status != "RESOLVED":
        return "REOPENED"
    return "STATUS_CHANGED"


def _dataset_digest(
    tickets: Iterable[TicketRow], events: Iterable[LifecycleEventRow]
) -> str:
    digest = hashlib.sha256()
    for ticket in tickets:
        digest.update(
            "|".join(
                (
                    str(ticket.ticket_id),
                    ticket.status,
                    ticket.reported_priority or "",
                    ticket.predicted_priority,
                    ticket.predicted_category,
                    str(ticket.prediction_confidence),
                    ticket.created_at.isoformat(),
                    ticket.updated_at.isoformat(),
                )
            ).encode()
        )
        digest.update(b"\n")
    for event in events:
        digest.update(
            "|".join(
                (
                    str(event.event_id),
                    str(event.ticket_id),
                    event.event_type,
                    event.previous_status or "",
                    event.current_status,
                    event.occurred_at.isoformat(),
                )
            ).encode()
        )
        digest.update(b"\n")
    return digest.hexdigest()


def _parse_anchor(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("anchor must include a timezone")
    return parsed.astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic, non-sensitive ticket lifecycle analytics data."
    )
    parser.add_argument("--event-count", type=int, default=DEFAULT_EVENT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--anchor", type=_parse_anchor, default=DEFAULT_ANCHOR)
    parser.add_argument(
        "--database-url",
        default=os.getenv("ANALYTICS_DATABASE_URL"),
        help="PostgreSQL URL; omit it to generate and report without loading.",
    )
    args = parser.parse_args()

    dataset = generate_dataset(args.event_count, args.seed, args.anchor)
    print(
        f"Generated {len(dataset.tickets)} tickets and {len(dataset.events)} lifecycle "
        f"events (sha256={dataset.digest})."
    )
    if args.database_url:
        inserted_tickets, inserted_events = load_dataset(dataset, args.database_url)
        print(
            f"Loaded {inserted_tickets} new tickets and {inserted_events} new lifecycle "
            "events; deterministic IDs make repeated runs idempotent."
        )


if __name__ == "__main__":
    main()
