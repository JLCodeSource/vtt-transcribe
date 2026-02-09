"""Tests for FastAPI backend."""

import io
import time
from unittest.mock import Mock, patch

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

    with patch("vtt_transcribe.api.VideoTranscriber"):
        # Create a mock audio file
        audio_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(audio_content), "audio/mpeg")}
        data = {"api_key": "test-api-key"}

        response = client.post("/transcribe", files=files, data=data)

        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "pending"


def test_get_job_status_returns_job_details() -> None:
    """Test that getting job status returns job details."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    with patch("vtt_transcribe.api.VideoTranscriber") as mock_transcriber_class:
        # Mock transcriber to return fake transcript text
        mock_transcriber = Mock()
        mock_transcriber.transcribe.return_value = "Test transcript text"
        mock_transcriber_class.return_value = mock_transcriber

        # First create a job
        audio_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(audio_content), "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        create_response = client.post("/transcribe", files=files, data=data)
        job_id = create_response.json()["job_id"]

        # Immediately get its status (before background task completes)
        status_response = client.get(f"/jobs/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        # Status could be pending, processing, or completed depending on timing
        assert data["status"] in ("pending", "processing", "completed")
        assert data["filename"] == "test.mp3"


def test_background_transcription_processes_file() -> None:
    """Test that uploaded file gets transcribed in background."""
    from vtt_transcribe.api import app

    client = TestClient(app)

    # Mock the transcriber to return a fake transcript
    mock_transcript_text = "Hello world"

    with patch("vtt_transcribe.api.VideoTranscriber") as mock_transcriber_class:
        mock_transcriber = Mock()
        mock_transcriber.transcribe.return_value = mock_transcript_text
        mock_transcriber_class.return_value = mock_transcriber

        # Upload file with API key
        audio_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(audio_content), "audio/mpeg")}
        data = {"api_key": "test-api-key"}

        response = client.post("/transcribe", files=files, data=data)
        job_id = response.json()["job_id"]

        # Wait briefly for background task
        time.sleep(0.5)

        # Check status - should now be complete
        status_response = client.get(f"/jobs/{job_id}")
        job_data = status_response.json()

        assert job_data["status"] == "completed"
        assert "transcript" in job_data
        assert job_data["transcript"]["text"] == "Hello world"
