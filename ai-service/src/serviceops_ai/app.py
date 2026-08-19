from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from serviceops_ai.kafka_worker import KafkaPredictionWorker
from serviceops_ai.knowledge import KnowledgeBase
from serviceops_ai.model import CATEGORIES, ModelBundle, load_or_train_model
from serviceops_ai.schemas import (
    HealthResponse,
    KnowledgeAnswerResponse,
    KnowledgeCitationResponse,
    KnowledgeQuestionRequest,
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
KNOWLEDGE_PATH = Path(
    os.getenv("KNOWLEDGE_PATH", str(AI_SERVICE_ROOT / "knowledge"))
)

model: ModelBundle | None = None
worker: KafkaPredictionWorker | None = None
knowledge_base: KnowledgeBase | None = None
tracer = trace.get_tracer(__name__)
HTTP_REQUESTS = Counter(
    "serviceops_http_requests",
    "Completed ServiceOps HTTP requests",
    ("service_name", "method", "route", "status_code"),
)
HTTP_DURATION = Histogram(
    "serviceops_http_request_duration_seconds",
    "ServiceOps HTTP request duration",
    ("service_name", "method", "route", "status_code"),
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, float("inf")),
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global knowledge_base, model, worker
    model = load_or_train_model(DATASET_PATH, MODEL_PATH)
    knowledge_base = KnowledgeBase(KNOWLEDGE_PATH)
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
    version="0.2.0",
    description="Educational prediction baseline and citation-grounded knowledge assistant.",
    lifespan=lifespan,
)


@app.middleware("http")
async def observe_http_request(request: Request, call_next):
    if request.url.path in {"/health", "/metrics"}:
        return await call_next(request)

    started_at = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "UNKNOWN")
        labels = (
            "serviceops-ai-service",
            request.method,
            route_path,
            str(status_code),
        )
        HTTP_REQUESTS.labels(*labels).inc()
        HTTP_DURATION.labels(*labels).observe(time.perf_counter() - started_at)


def require_model() -> ModelBundle:
    if model is None:
        raise RuntimeError("Model has not been initialized")
    return model


def require_knowledge_base() -> KnowledgeBase:
    if knowledge_base is None:
        raise RuntimeError("Knowledge base has not been initialized")
    return knowledge_base


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
    knowledge_ready = knowledge_base is not None
    if model is None or not knowledge_ready or (kafka_enabled and not worker_ready):
        raise HTTPException(status_code=503, detail="AI service is not ready")
    current_knowledge = require_knowledge_base()
    return HealthResponse(
        status="UP",
        modelLoaded=model is not None,
        kafkaWorkerRunning=worker_ready if kafka_enabled else False,
        knowledgeBaseReady=knowledge_ready,
        knowledgeDocuments=current_knowledge.document_count,
        knowledgeChunks=len(current_knowledge.chunks),
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
        dataset="Bundled deterministic synthetic support-ticket corpus",
    )


@app.post("/knowledge/ask", response_model=KnowledgeAnswerResponse)
def ask_knowledge(
    request: KnowledgeQuestionRequest,
    _: Annotated[AuthenticatedUser, Depends(viewer_or_operator)],
) -> KnowledgeAnswerResponse:
    with tracer.start_as_current_span("serviceops.knowledge.answer") as span:
        current = require_knowledge_base()
        result = current.ask(request.question)
        span.set_attribute("serviceops.rag.grounded", result.grounded)
        span.set_attribute("serviceops.rag.citation_count", len(result.citations))
        return KnowledgeAnswerResponse(
            answer=result.answer,
            grounded=result.grounded,
            citations=[
                KnowledgeCitationResponse(
                    documentId=citation.document_id,
                    title=citation.title,
                    section=citation.section,
                    revision=citation.revision,
                    sourcePath=citation.source_path,
                    excerpt=citation.excerpt,
                    relevance=citation.relevance,
                )
                for citation in result.citations
            ],
            indexVersion=current.index_version,
        )
