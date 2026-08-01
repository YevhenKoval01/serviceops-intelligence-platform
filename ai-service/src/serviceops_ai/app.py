from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from serviceops_ai.kafka_worker import KafkaPredictionWorker
from serviceops_ai.model import CATEGORIES, ModelBundle, load_or_train_model
from serviceops_ai.schemas import (
    HealthResponse,
    ModelInfoResponse,
    PredictionRequest,
    PredictionResponse,
)
from serviceops_ai.security import AuthenticatedUser, operator, viewer_or_operator

AI_SERVICE_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = Path(
    os.getenv(
        "DATASET_PATH",
        str(AI_SERVICE_ROOT / "data" / "training_tickets.csv"),
    )
)
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(AI_SERVICE_ROOT / "model" / "baseline.joblib")))

model: ModelBundle | None = None
worker: KafkaPredictionWorker | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model, worker
    model = load_or_train_model(DATASET_PATH, MODEL_PATH)
    if os.getenv("KAFKA_ENABLED", "true").lower() == "true":
        worker = KafkaPredictionWorker(
            model,
            os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),
        )
        worker.start()
    yield
    if worker is not None:
        worker.stop()


app = FastAPI(
    title="ServiceOps AI API",
    version="0.1.0",
    description="Educational scikit-learn ticket category and priority baseline.",
    lifespan=lifespan,
)


def require_model() -> ModelBundle:
    if model is None:
        raise RuntimeError("Model has not been initialized")
    return model


@app.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    _: Annotated[AuthenticatedUser, Depends(operator)],
) -> PredictionResponse:
    return require_model().predict(request.title, request.description)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    kafka_enabled = os.getenv("KAFKA_ENABLED", "true").lower() == "true"
    worker_ready = worker is not None and worker.is_ready
    if model is None or (kafka_enabled and not worker_ready):
        raise HTTPException(status_code=503, detail="Prediction service is not ready")
    return HealthResponse(
        status="UP",
        modelLoaded=model is not None,
        kafkaWorkerRunning=worker_ready if kafka_enabled else False,
    )


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info(
    _: Annotated[AuthenticatedUser, Depends(viewer_or_operator)],
) -> ModelInfoResponse:
    current = require_model()
    return ModelInfoResponse(
        modelVersion=current.model_version,
        algorithm="TfidfVectorizer + LogisticRegression",
        categories=CATEGORIES,
        trainingRows=current.training_rows,
        validationAccuracy=current.metrics,
        dataset="Bundled synthetic, non-sensitive support tickets",
    )
