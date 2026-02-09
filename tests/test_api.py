"""Tests for FastAPI application."""

import io

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


def test_upload_audio_file_success() -> None:
    """Test successful audio file upload."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # Create a fake MP3 file
    fake_mp3_content = b"fake mp3 content for testing"
    files = {"file": ("test.mp3", io.BytesIO(fake_mp3_content), "audio/mpeg")}

    response = client.post("/api/v1/transcribe", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert data["status"] == "pending"


def test_upload_video_file_success() -> None:
    """Test successful video file upload."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # Create a fake MP4 file
    fake_mp4_content = b"fake mp4 content for testing"
    files = {"file": ("test.mp4", io.BytesIO(fake_mp4_content), "video/mp4")}

    response = client.post("/api/v1/transcribe", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "status" in data


def test_upload_invalid_file_type() -> None:
    """Test rejection of unsupported file type."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # Create a fake text file (unsupported)
    fake_content = b"not a valid audio/video file"
    files = {"file": ("test.txt", io.BytesIO(fake_content), "text/plain")}

    response = client.post("/api/v1/transcribe", files=files)

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_without_file() -> None:
    """Test endpoint requires file upload."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    response = client.post("/api/v1/transcribe")

    assert response.status_code == 422  # Unprocessable Entity


def test_upload_file_too_large() -> None:
    """Test rejection of files exceeding size limit."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # Create a file larger than typical limits (e.g., 100MB)
    # For testing, we'll simulate this with metadata
    large_content = b"x" * (101 * 1024 * 1024)  # 101MB
    files = {"file": ("large.mp3", io.BytesIO(large_content), "audio/mpeg")}

    response = client.post("/api/v1/transcribe", files=files)

    # Should either reject immediately or handle gracefully
    assert response.status_code in [400, 413]  # Bad Request or Payload Too Large
