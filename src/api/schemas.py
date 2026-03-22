"""Pydantic schemas for the API."""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., description="Your Ayurveda question", min_length=1)
    top_k: int = Field(5, description="Number of sources to retrieve", ge=1, le=20)
    evaluate: bool = Field(True, description="Run quality evaluation on the response")


class SourceInfo(BaseModel):
    file: str
    section: str
    score: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceInfo]
    model: str
    latency_ms: float
    evaluation: dict | None = None


class ImageQueryRequest(BaseModel):
    question: str = "What does this image show and what is its Ayurvedic significance?"


class ImageQueryResponse(BaseModel):
    image_content: str
    sources: list[SourceInfo]
    vision_model: str


class IngestResponse(BaseModel):
    message: str
    chunks_added: int
    total_chunks: int


class StatusResponse(BaseModel):
    vector_store: dict
    answer_llm: dict
    monitor_llm: dict


class StatsResponse(BaseModel):
    total_queries: int
    total_errors: int
    error_rate: float
    avg_latency_ms: float
    avg_quality_score: float
    evaluated_queries: int
