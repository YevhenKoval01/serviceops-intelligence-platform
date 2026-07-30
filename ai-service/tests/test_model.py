from pathlib import Path

from serviceops_ai.model import train_model

DATASET = Path(__file__).parents[1] / "data" / "training_tickets.csv"


def test_training_is_deterministic() -> None:
    first = train_model(DATASET)
    second = train_model(DATASET)
    sample = (
        "Production API unavailable",
        "Every request fails and customers cannot complete their orders.",
    )

    assert first.metrics == second.metrics
    assert first.predict(*sample) == second.predict(*sample)


def test_prediction_matches_response_contract() -> None:
    model = train_model(DATASET)

    prediction = model.predict(
        "Cannot access account",
        "The user is locked out after replacing the authentication device.",
    )

    assert prediction.category in {"ACCESS", "BILLING", "DELIVERY", "TECHNICAL"}
    assert prediction.priority in {"LOW", "MEDIUM", "HIGH"}
    assert 0 <= prediction.confidence <= 1
    assert prediction.modelVersion == "baseline-1"
