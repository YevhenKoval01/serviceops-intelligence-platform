from pathlib import Path

from serviceops_ai.model import CATEGORIES, load_dataset

DATASET = Path(__file__).parents[1] / "data" / "training_tickets.csv"


def test_dataset_has_expected_schema_and_labels() -> None:
    data = load_dataset(DATASET)

    assert len(data) == 40
    assert sorted(data["category"].unique()) == CATEGORIES
    assert set(data["priority"].unique()) == {"LOW", "MEDIUM", "HIGH"}
    assert data[["title", "description", "category", "priority"]].isnull().sum().sum() == 0
