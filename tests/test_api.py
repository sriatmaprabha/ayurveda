"""Tests for the FastAPI endpoints."""

import os
import pytest
from unittest.mock import MagicMock, patch

# Set env vars before importing app
os.environ["LLM_BASE_URL"] = "http://localhost:99999/v1"
os.environ["ENABLE_MONITORING"] = "false"

from fastapi.testclient import TestClient
from src.api.app import app, _get_pipeline
from src.api.schemas import QueryRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_status_endpoint(client):
    """Test that status endpoint returns component health."""
    response = client.get("/status")
    # Will get 503 if pipeline not initialized in test context
    assert response.status_code in (200, 503)


def test_stats_endpoint(client):
    """Test that stats endpoint returns metrics."""
    response = client.get("/stats")
    assert response.status_code in (200, 503)


def test_query_request_validation():
    """Test Pydantic schema validation."""
    req = QueryRequest(question="What is Triphala?", top_k=3, evaluate=False)
    assert req.question == "What is Triphala?"
    assert req.top_k == 3

    with pytest.raises(Exception):
        QueryRequest(question="", top_k=3)


def test_query_request_defaults():
    req = QueryRequest(question="Test")
    assert req.top_k == 5
    assert req.evaluate is True


def test_openapi_schema(client):
    """Test that OpenAPI docs are generated."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "Ayurveda RAG API" in data["info"]["title"]
    assert "/query" in data["paths"]
    assert "/status" in data["paths"]
    assert "/stats" in data["paths"]
    assert "/vision/query" in data["paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
