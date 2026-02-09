"""Tests for FastAPI application."""

from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    """Test that health endpoint returns OK status."""
    from vtt_transcribe.api import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_docs_available() -> None:
    """Test that OpenAPI documentation is available."""
    from vtt_transcribe.api import app

    client = TestClient(app)
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_json_schema() -> None:
    """Test that OpenAPI JSON schema is available."""
    from vtt_transcribe.api import app

    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "VTT Transcribe API"
    assert "paths" in response.json()
    assert "/health" in response.json()["paths"]
