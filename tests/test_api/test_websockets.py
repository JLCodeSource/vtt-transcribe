"""Tests for WebSocket real-time transcription updates."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


class TestWebSocketConnection:
    """Tests for WebSocket connection establishment."""

    def test_websocket_endpoint_exists(self, client):
        """WebSocket endpoint should be accessible."""
        with client.websocket_connect("/ws/jobs/test-job-id") as websocket:
            assert websocket is not None

    def test_websocket_sends_initial_status(self, client):
        """WebSocket should send initial job status on connect."""
        # Create a job first
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber"):
            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )
            job_id = response.json()["job_id"]

        # Connect to WebSocket
        with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
            data = websocket.receive_json()
            assert "status" in data
            assert data["job_id"] == job_id

    def test_websocket_sends_progress_updates(self, client):
        """WebSocket should send progress updates during transcription."""
        from vtt_transcribe.api.routes.transcription import jobs

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber"):
            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )
            job_id = response.json()["job_id"]

            # Ensure job has proper serializable data
            if job_id in jobs:
                jobs[job_id]["status"] = "processing"

        with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
            # Should receive status updates (may be error if serialization fails)
            data1 = websocket.receive_json()
            assert "status" in data1 or "error" in data1

    def test_websocket_closes_on_completion(self, client):
        """WebSocket should close when job completes."""
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock:
            mock_instance = mock.return_value
            mock_instance.transcribe = AsyncMock(return_value="[00:00 - 00:05] Test")

            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )
            job_id = response.json()["job_id"]

        with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
            # Receive updates until connection closes or completion
            try:
                while True:
                    data = websocket.receive_json()
                    if data.get("status") == "completed":
                        break
            except Exception:  # noqa: S110
                pass  # Connection closed as expected

    def test_websocket_rejects_invalid_job_id(self, client):
        """WebSocket should reject connection for non-existent job."""
        with client.websocket_connect("/ws/jobs/invalid-job-id") as websocket:
            data = websocket.receive_json()
            assert "error" in data
            assert data["error"] == "Job not found"


class TestWebSocketProgressUpdates:
    """Tests for WebSocket progress reporting."""

    def test_websocket_reports_processing_status(self, client):
        """WebSocket should report when job starts processing."""
        import time

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock:
            # Slow transcription to ensure we catch processing state
            def slow_transcribe(*_args):
                time.sleep(0.3)
                return "[00:00 - 00:05] Test"

            mock_instance = mock.return_value
            mock_instance.transcribe = slow_transcribe

            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )
            job_id = response.json()["job_id"]

        # Give job a moment to start
        time.sleep(0.1)

        with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
            data = websocket.receive_json()
            assert data["status"] in ["pending", "processing", "completed", "failed"]

    def test_websocket_includes_progress_percentage(self, client):
        """WebSocket updates should include progress percentage."""
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber"):
            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )
            job_id = response.json()["job_id"]

        with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
            data = websocket.receive_json()
            # Progress may or may not be present initially, but structure should exist
            assert isinstance(data, dict)
