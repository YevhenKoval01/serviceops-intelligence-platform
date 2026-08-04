from datetime import UTC, datetime

import pytest

from serviceops_analytics.generator import generate_dataset


def test_generates_at_least_one_hundred_thousand_valid_lifecycle_events() -> None:
    dataset = generate_dataset()

    assert len(dataset.events) == 100_000
    assert len(dataset.tickets) == 40_000
    assert len({ticket.ticket_id for ticket in dataset.tickets}) == 40_000
    assert len({event.event_id for event in dataset.events}) == 100_000
    assert any(event.event_type == "REOPENED" for event in dataset.events)
    assert all(ticket.created_at <= ticket.updated_at for ticket in dataset.tickets)


def test_generation_is_reproducible_for_seed_and_anchor() -> None:
    anchor = datetime(2026, 7, 31, tzinfo=UTC)

    first = generate_dataset(event_count=200, seed=42, anchor=anchor)
    second = generate_dataset(event_count=200, seed=42, anchor=anchor)
    changed = generate_dataset(event_count=200, seed=43, anchor=anchor)

    assert first.digest == second.digest
    assert first.tickets == second.tickets
    assert first.events == second.events
    assert changed.digest != first.digest


def test_each_event_chain_has_consistent_transitions() -> None:
    dataset = generate_dataset(event_count=1_000)
    events_by_ticket: dict[object, list[object]] = {}
    for event in dataset.events:
        events_by_ticket.setdefault(event.ticket_id, []).append(event)

    for events in events_by_ticket.values():
        assert events[0].event_type == "CREATED"
        assert events[0].previous_status is None
        for previous, current in zip(events, events[1:], strict=False):
            assert current.previous_status == previous.current_status
            assert current.occurred_at > previous.occurred_at


def test_rejects_invalid_generation_inputs() -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_dataset(event_count=0)
    with pytest.raises(ValueError, match="timezone"):
        generate_dataset(anchor=datetime(2026, 7, 31))
