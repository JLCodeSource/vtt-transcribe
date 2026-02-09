"""Tests for FastAPI backend."""

import io

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok() -> None:
    """Test that health check endpoint returns 200 OK."""
    from vtt_transcribe.api import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_file_creates_transcription_job() -> None:
    """Test that uploading a file creates a transcription job."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # Create a mock audio file
    audio_content = b"fake audio content"
    files = {"file": ("test.mp3", io.BytesIO(audio_content), "audio/mpeg")}

    response = client.post("/transcribe", files=files)

    assert response.status_code == 202  # Accepted
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert data["status"] == "pending"


def test_get_job_status_returns_job_details() -> None:
    """Test that getting job status returns job details."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # First create a job
    audio_content = b"fake audio content"
    files = {"file": ("test.mp3", io.BytesIO(audio_content), "audio/mpeg")}
    create_response = client.post("/transcribe", files=files)
    job_id = create_response.json()["job_id"]

    # Then get its status
    status_response = client.get(f"/jobs/{job_id}")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"
    assert data["filename"] == "test.mp3"
