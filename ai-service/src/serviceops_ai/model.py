from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

from serviceops_ai.schemas import PredictionResponse

MODEL_VERSION = "baseline-2"
REQUIRED_COLUMNS = {"scenario_id", "title", "description", "category", "priority"}
CATEGORIES = ["ACCESS", "BILLING", "DELIVERY", "TECHNICAL"]
VALIDATION_SEED = "serviceops-validation-2026"


@dataclass
class ModelBundle:
    category_pipeline: Pipeline
    priority_pipeline: Pipeline
    metrics: dict[str, float]
    training_rows: int
    dataset_digest: str
    model_version: str = MODEL_VERSION

    def predict(self, title: str, description: str) -> PredictionResponse:
        text = pd.Series([combine_text(title, description)])
        category = str(self.category_pipeline.predict(text)[0])
        category_probabilities = self.category_pipeline.predict_proba(text)[0]
        confidence = round(float(max(category_probabilities)), 5)
        priority = str(self.priority_pipeline.predict(text)[0])
        return PredictionResponse(
            category=category,
            priority=priority,
            confidence=confidence,
            modelVersion=self.model_version,
        )


def combine_text(title: str, description: str) -> str:
    return f"{title.strip()} {description.strip()}"


def load_dataset(dataset_path: Path) -> pd.DataFrame:
    data = pd.read_csv(dataset_path)
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    if data[list(REQUIRED_COLUMNS)].isnull().any().any():
        raise ValueError("Dataset contains null values")
    if any(
        data[column].astype(str).str.strip().eq("").any() for column in REQUIRED_COLUMNS
    ):
        raise ValueError("Dataset contains empty values")
    if set(data["category"]) != set(CATEGORIES):
        raise ValueError("Dataset must contain exactly the four baseline categories")
    if not set(data["priority"]).issubset({"LOW", "MEDIUM", "HIGH"}):
        raise ValueError("Dataset contains an unsupported priority")
    if data.duplicated(subset=["title", "description"]).any():
        raise ValueError("Dataset contains duplicate ticket text")

    scenario_labels = data.groupby("scenario_id")[["category", "priority"]].nunique()
    if scenario_labels.gt(1).any().any():
        raise ValueError("Each scenario id must map to exactly one category and priority")
    return data


def split_dataset_by_scenario(data: pd.DataFrame) -> tuple[pd.Index, pd.Index]:
    scenario_labels = data[["scenario_id", "category", "priority"]].drop_duplicates()
    validation_groups: set[str] = set()
    for (category, priority), label_group in scenario_labels.groupby(["category", "priority"]):
        scenario_ids = label_group["scenario_id"].tolist()
        if len(scenario_ids) < 2:
            raise ValueError(
                f"Dataset needs at least two scenarios for {category}/{priority}"
            )
        validation_groups.add(
            min(
                scenario_ids,
                key=lambda scenario_id: hashlib.sha256(
                    f"{VALIDATION_SEED}:{scenario_id}".encode()
                ).digest(),
            )
        )

    validation_mask = data["scenario_id"].isin(validation_groups)
    return data.index[~validation_mask], data.index[validation_mask]


def make_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    lowercase=True,
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                    solver="liblinear",
                ),
            ),
        ]
    )


def train_model(dataset_path: Path) -> ModelBundle:
    data = load_dataset(dataset_path).copy()
    text = data.apply(lambda row: combine_text(row["title"], row["description"]), axis=1)
    train_indexes, validation_indexes = split_dataset_by_scenario(data)

    category_pipeline = make_pipeline()
    category_pipeline.fit(text.loc[train_indexes], data.loc[train_indexes, "category"])
    category_predictions = category_pipeline.predict(text.loc[validation_indexes])

    priority_pipeline = make_pipeline()
    priority_pipeline.fit(text.loc[train_indexes], data.loc[train_indexes, "priority"])
    priority_predictions = priority_pipeline.predict(text.loc[validation_indexes])

    return ModelBundle(
        category_pipeline=category_pipeline,
        priority_pipeline=priority_pipeline,
        metrics={
            "categoryAccuracy": round(
                float(
                    accuracy_score(
                        data.loc[validation_indexes, "category"],
                        category_predictions,
                    )
                ),
                4,
            ),
            "priorityAccuracy": round(
                float(
                    accuracy_score(
                        data.loc[validation_indexes, "priority"],
                        priority_predictions,
                    )
                ),
                4,
            ),
        },
        training_rows=len(data),
        dataset_digest=_dataset_digest(dataset_path),
    )


def load_or_train_model(dataset_path: Path, model_path: Path) -> ModelBundle:
    current_digest = _dataset_digest(dataset_path)
    if model_path.exists():
        bundle: Any = joblib.load(model_path)
        if (
            isinstance(bundle, ModelBundle)
            and bundle.model_version == MODEL_VERSION
            and getattr(bundle, "dataset_digest", None) == current_digest
        ):
            return bundle
    bundle = train_model(dataset_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    return bundle


def _dataset_digest(dataset_path: Path) -> str:
    return hashlib.sha256(dataset_path.read_bytes()).hexdigest()
