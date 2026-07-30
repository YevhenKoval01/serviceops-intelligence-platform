from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from serviceops_ai.schemas import PredictionResponse

MODEL_VERSION = "baseline-1"
REQUIRED_COLUMNS = {"title", "description", "category", "priority"}
CATEGORIES = ["ACCESS", "BILLING", "DELIVERY", "TECHNICAL"]


@dataclass
class ModelBundle:
    category_pipeline: Pipeline
    priority_pipeline: Pipeline
    metrics: dict[str, float]
    training_rows: int
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
    if set(data["category"]) != set(CATEGORIES):
        raise ValueError("Dataset must contain exactly the four baseline categories")
    if not set(data["priority"]).issubset({"LOW", "MEDIUM", "HIGH"}):
        raise ValueError("Dataset contains an unsupported priority")
    return data


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
    train_indexes, validation_indexes = train_test_split(
        data.index,
        test_size=0.25,
        random_state=42,
        stratify=data["category"],
    )

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
    )


def load_or_train_model(dataset_path: Path, model_path: Path) -> ModelBundle:
    if model_path.exists():
        bundle: Any = joblib.load(model_path)
        if isinstance(bundle, ModelBundle) and bundle.model_version == MODEL_VERSION:
            return bundle
    bundle = train_model(dataset_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    return bundle
