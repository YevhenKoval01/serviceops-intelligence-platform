from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["ACCESS", "BILLING", "DELIVERY", "TECHNICAL"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]


class PredictionRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Production API unavailable",
                    "description": (
                        "Every customer API request returns a server error "
                        "and order processing is blocked."
                    ),
                }
            ]
        },
    )

    title: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=10, max_length=4000)


class PredictionResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "category": "TECHNICAL",
                    "priority": "HIGH",
                    "confidence": 0.87542,
                    "modelVersion": "baseline-1",
                }
            ]
        }
    )

    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    modelVersion: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "UP",
                    "modelLoaded": True,
                    "kafkaWorkerRunning": True,
                    "knowledgeBaseReady": True,
                    "knowledgeDocuments": 6,
                    "knowledgeChunks": 18,
                }
            ]
        }
    )

    status: Literal["UP"]
    modelLoaded: bool
    kafkaWorkerRunning: bool
    knowledgeBaseReady: bool
    knowledgeDocuments: int = Field(ge=1)
    knowledgeChunks: int = Field(ge=1)


class ModelInfoResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "modelVersion": "baseline-1",
                    "algorithm": "TfidfVectorizer + LogisticRegression",
                    "categories": ["ACCESS", "BILLING", "DELIVERY", "TECHNICAL"],
                    "trainingRows": 40,
                    "validationAccuracy": {
                        "categoryAccuracy": 0.6,
                        "priorityAccuracy": 0.5,
                    },
                    "dataset": "Bundled synthetic, non-sensitive support tickets",
                }
            ]
        }
    )

    modelVersion: str
    algorithm: str
    categories: list[str]
    trainingRows: int
    validationAccuracy: dict[str, float]
    dataset: str


class KnowledgeQuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=5, max_length=500)


class KnowledgeCitationResponse(BaseModel):
    documentId: str
    title: str
    section: str
    revision: str
    sourcePath: str
    excerpt: str
    relevance: float = Field(ge=0.0, le=1.0)


class KnowledgeAnswerResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[KnowledgeCitationResponse]
    indexVersion: str
