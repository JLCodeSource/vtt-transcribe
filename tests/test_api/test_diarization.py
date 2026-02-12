"""Tests for diarization API endpoints."""

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_hf_token(monkeypatch):
    """Clear HF_TOKEN environment variable to prevent test interference."""
    monkeypatch.delenv("HF_TOKEN", raising=False)


class TestDiarizationEndpoint:
    """Tests for diarization-enabled transcription."""

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_with_diarization_requires_hf_token(self, _mock_transcriber, client):  # noqa: PT019
        """POST /transcribe with diarize=true should require HF token."""
        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
            data={"api_key": "test-key", "diarize": "true"},
        )
        assert response.status_code == 400
        assert "huggingface" in response.json()["detail"].lower() or "hf_token" in response.json()["detail"].lower()

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_with_diarization_accepts_hf_token(self, mock_transcriber, client):
        """POST /transcribe with diarize=true and hf_token should succeed."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Speaker 1: Test"

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
            data={"api_key": "test-key", "diarize": "true", "hf_token": "hf_test_token"},
        )
        assert response.status_code in [200, 201, 202]
        assert "job_id" in response.json()

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_with_diarization_uses_env_token(self, mock_transcriber, client, monkeypatch):
        """POST /transcribe with diarize=true should use HF_TOKEN env var if no token provided."""
        monkeypatch.setenv("HF_TOKEN", "hf_env_token")
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Speaker 1: Test"

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
            data={"api_key": "test-key", "diarize": "true"},
        )
        assert response.status_code in [200, 201, 202]
        assert "job_id" in response.json()

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_with_diarization_device_parameter(self, mock_transcriber, client):
        """POST /transcribe with device parameter should be accepted."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Speaker 1: Test"

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
            data={
                "api_key": "test-key",
                "diarize": "true",
                "hf_token": "hf_test_token",
                "device": "cpu",
            },
        )
        assert response.status_code in [200, 201, 202]


class TestDiarizeOnlyEndpoint:
    """Tests for diarization-only endpoint."""

    def test_diarize_endpoint_exists(self, client):
        """POST /diarize endpoint should exist."""
        response = client.post("/api/diarize")
        assert response.status_code in [400, 422]  # Bad request or validation error, but endpoint exists

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_diarize_requires_hf_token(self, _mock_transcriber, client):  # noqa: PT019
        """POST /diarize should require HF token."""
        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
        )
        assert response.status_code in [400, 422]

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_diarize_with_hf_token_succeeds(self, mock_transcriber, client):
        """POST /diarize with HF token should succeed."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Speaker 1: Test"

        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
            data={"hf_token": "hf_test_token"},
        )
        assert response.status_code in [200, 201, 202]
        assert "job_id" in response.json()

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_diarize_with_device_parameter(self, mock_transcriber, client):
        """POST /diarize with device parameter should be accepted."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Speaker 1: Test"

        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
            data={"hf_token": "hf_test_token", "device": "cpu"},
        )
        assert response.status_code in [200, 201, 202]

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_diarize_uses_env_token(self, mock_transcriber, client, monkeypatch):
        """POST /diarize should use HF_TOKEN env var when no token provided."""
        monkeypatch.setenv("HF_TOKEN", "hf_env_token")
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Speaker 1: Test"

        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
        )
        assert response.status_code in [200, 201, 202]
        assert "job_id" in response.json()
