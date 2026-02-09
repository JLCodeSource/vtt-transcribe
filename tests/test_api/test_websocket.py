"""Tests for WebSocket endpoints."""

import tempfile

from fastapi.testclient import TestClient


def test_websocket_job_status_connection() -> None:
    """Test that WebSocket connection can be established for job status."""
    from vtt_transcribe.api.app import app

    client = TestClient(app)

    with client.websocket_connect("/ws/jobs/test-job-id") as websocket:
        # Should connect successfully
        assert websocket is not None


def test_websocket_receives_job_updates() -> None:
    """Test that WebSocket receives job status updates."""
    from vtt_transcribe.api.app import app

    client = TestClient(app)

    # Create a job first
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"fake audio content")
        temp_path = f.name

    with open(temp_path, "rb") as f:
        response = client.post(
            "/transcribe",
            files={"file": ("test.mp3", f, "audio/mpeg")},
            data={"api_key": "test-key"},
        )

    job_id = response.json()["job_id"]

    # Connect to WebSocket for this job
    with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
        # Should receive initial status
        data = websocket.receive_json()
        assert data["job_id"] == job_id
        assert "status" in data

        # Should receive progress updates
        # (In real scenario, would wait for processing updates)
        websocket.close()


def test_websocket_handles_invalid_job_id() -> None:
    """Test that WebSocket handles invalid job ID gracefully."""
    from vtt_transcribe.api.app import app

    client = TestClient(app)

    with client.websocket_connect("/ws/jobs/invalid-job-id") as websocket:
        # Should receive error message
        data = websocket.receive_json()
        assert "error" in data or data.get("status") == "not_found"
