"""Tests for FastAPI backend."""

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok() -> None:
    """Test that health check endpoint returns 200 OK."""
    from vtt_transcribe.api import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
