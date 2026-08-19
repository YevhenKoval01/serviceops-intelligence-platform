import hashlib
from pathlib import Path

from serviceops_ai.model import load_or_train_model, train_model

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
    assert prediction.modelVersion == "baseline-2"


def test_model_cache_is_invalidated_when_dataset_changes(tmp_path: Path) -> None:
    dataset = tmp_path / "training_tickets.csv"
    dataset.write_bytes(DATASET.read_bytes())
    model_path = tmp_path / "baseline.joblib"

    first = load_or_train_model(dataset, model_path)
    dataset.write_bytes(dataset.read_bytes() + b"\n")
    second = load_or_train_model(dataset, model_path)

    assert first.dataset_digest != second.dataset_digest
    assert second.dataset_digest == hashlib.sha256(dataset.read_bytes()).hexdigest()
