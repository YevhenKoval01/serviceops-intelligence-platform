from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["ACCESS", "BILLING", "DELIVERY", "TECHNICAL"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]


class PredictionRequest(BaseModel):
    title: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=10, max_length=4000)


class PredictionResponse(BaseModel):
    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    modelVersion: str


class HealthResponse(BaseModel):
    status: Literal["UP"]
    modelLoaded: bool
    kafkaWorkerRunning: bool


class ModelInfoResponse(BaseModel):
    modelVersion: str
    algorithm: str
    categories: list[str]
    trainingRows: int
    validationAccuracy: dict[str, float]
    dataset: str
