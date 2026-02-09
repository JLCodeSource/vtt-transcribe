"""Tests for transcription API endpoints."""

import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


@pytest.fixture
def sample_audio_file():
    """Create sample audio file bytes for testing."""
    return io.BytesIO(b"fake audio data")


class TestTranscribeEndpoint:
    """Tests for /transcribe endpoint."""

    def test_transcribe_endpoint_exists(self, client):
        """POST /transcribe endpoint should exist."""
        response = client.post("/transcribe")
        assert response.status_code != 404

    def test_transcribe_requires_file(self, client):
        """POST /transcribe should require a file upload."""
        response = client.post("/transcribe")
        assert response.status_code == 422

    def test_transcribe_requires_api_key(self, client, sample_audio_file):
        """POST /transcribe should require OpenAI API key."""
        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        response = client.post("/transcribe", files=files)
        assert response.status_code == 422
        data = response.json()
        assert "api_key" in str(data).lower() or "detail" in data

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_accepts_audio_file(self, mock_transcriber, client, sample_audio_file):
        """POST /transcribe should accept audio file with API key."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/transcribe", files=files, data=data)

        assert response.status_code in [200, 201, 202]

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_returns_job_id(self, mock_transcriber, client, sample_audio_file):
        """POST /transcribe should return a job ID for async processing."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/transcribe", files=files, data=data)

        response_data = response.json()
        assert "job_id" in response_data
        assert isinstance(response_data["job_id"], str)

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_returns_status(self, mock_transcriber, client, sample_audio_file):
        """POST /transcribe should return job status."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/transcribe", files=files, data=data)

        response_data = response.json()
        assert "status" in response_data
        assert response_data["status"] in ["pending", "processing", "completed"]


class TestJobStatusEndpoint:
    """Tests for /jobs/{job_id} status endpoint."""

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_job_status_endpoint_exists(self, mock_transcriber, client, sample_audio_file):
        """GET /jobs/{job_id} endpoint should exist."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        create_response = client.post("/transcribe", files=files, data=data)
        job_id = create_response.json()["job_id"]

        response = client.get(f"/jobs/{job_id}")
        assert response.status_code != 404

    def test_job_status_returns_not_found_for_invalid_id(self, client):
        """GET /jobs/{job_id} should return 404 for non-existent job."""
        response = client.get("/jobs/nonexistent-job-id")
        assert response.status_code == 404

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_job_status_returns_job_info(self, mock_transcriber, client, sample_audio_file):
        """GET /jobs/{job_id} should return job information."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        create_response = client.post("/transcribe", files=files, data=data)
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/jobs/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "job_id" in status_data
        assert "status" in status_data


class TestSupportedFileTypes:
    """Tests for supported file type validation."""

    @pytest.mark.parametrize(
        ("filename", "mimetype"),
        [
            ("test.mp3", "audio/mpeg"),
            ("test.mp4", "video/mp4"),
            ("test.wav", "audio/wav"),
            ("test.m4a", "audio/mp4"),
            ("test.ogg", "audio/ogg"),
        ],
    )
    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_accepts_supported_audio_video_formats(self, mock_transcriber, client, filename, mimetype):
        """POST /transcribe should accept common audio/video formats."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        file_content = io.BytesIO(b"fake file data")
        files = {"file": (filename, file_content, mimetype)}
        data = {"api_key": "test-api-key"}
        response = client.post("/transcribe", files=files, data=data)

        assert response.status_code in [200, 201, 202]
