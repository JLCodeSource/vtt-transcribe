"""Tests for FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint_exists(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_status(self, client):
        """Health endpoint should return status in JSON."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_returns_version(self, client):
        """Health endpoint should return application version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint_exists(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_returns_welcome_message(self, client):
        """Root endpoint should return welcome message."""
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "vtt-transcribe" in data["message"].lower()


class TestAPIMetadata:
    """Tests for API metadata and documentation."""

    def test_openapi_schema_exists(self, client):
        """OpenAPI schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data

    def test_api_title_in_schema(self, client):
        """API should have proper title in OpenAPI schema."""
        response = client.get("/openapi.json")
        data = response.json()
        assert data["info"]["title"] == "vtt-transcribe API"

    def test_api_version_in_schema(self, client):
        """API should have version in OpenAPI schema."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "version" in data["info"]
