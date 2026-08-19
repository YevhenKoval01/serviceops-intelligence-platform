import hashlib
from pathlib import Path

from serviceops_ai.dataset import VARIANTS_PER_SCENARIO, write_dataset
from serviceops_ai.model import CATEGORIES, load_dataset, split_dataset_by_scenario

AI_SERVICE_ROOT = Path(__file__).parents[1]
SCENARIOS = AI_SERVICE_ROOT / "data" / "training_scenarios.csv"
DATASET = AI_SERVICE_ROOT / "data" / "training_tickets.csv"
DATASET_SHA256 = "e4eab186ac369f49209a5fbe4fdfaeb6505a6cb3a5796deefae97d2ef5ae3455"


def test_generated_dataset_is_current_and_reproducible(tmp_path: Path) -> None:
    regenerated = tmp_path / "training_tickets.csv"

    row_count = write_dataset(SCENARIOS, regenerated)

    assert row_count == 1_000
    assert regenerated.read_bytes() == DATASET.read_bytes()
    assert hashlib.sha256(regenerated.read_bytes()).hexdigest() == DATASET_SHA256


def test_dataset_has_expected_scale_schema_and_labels() -> None:
    data = load_dataset(DATASET)

    assert len(data) == 1_000
    assert data["scenario_id"].nunique() == 40
    assert set(data["scenario_id"].value_counts()) == {VARIANTS_PER_SCENARIO}
    assert sorted(data["category"].unique()) == CATEGORIES
    assert set(data["priority"].unique()) == {"LOW", "MEDIUM", "HIGH"}
    assert data[list(data.columns)].isnull().sum().sum() == 0
    assert data.duplicated(subset=["title", "description"]).sum() == 0


def test_validation_split_holds_out_complete_scenarios_for_every_label() -> None:
    data = load_dataset(DATASET)

    train_indexes, validation_indexes = split_dataset_by_scenario(data)
    train = data.loc[train_indexes]
    validation = data.loc[validation_indexes]

    assert len(train) == 700
    assert len(validation) == 300
    assert set(train["scenario_id"]).isdisjoint(validation["scenario_id"])
    assert validation["scenario_id"].nunique() == 12
    assert set(zip(validation["category"], validation["priority"], strict=True)) == {
        (category, priority)
        for category in CATEGORIES
        for priority in ("LOW", "MEDIUM", "HIGH")
    }
