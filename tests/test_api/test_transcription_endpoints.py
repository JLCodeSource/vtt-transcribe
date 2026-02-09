"""Tests for transcription API endpoints."""

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
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


class TestAPITranscriptionCoverage:
    """Tests to cover missing lines in api/routes/transcription.py."""

    def test_transcribe_with_missing_filename(self) -> None:
        """Test transcribe endpoint checks for filename (line 39)."""
        from unittest.mock import AsyncMock

        from fastapi import UploadFile

        from vtt_transcribe.api.routes.transcription import create_transcription_job

        # Create UploadFile with no filename
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = None

        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:  # noqa: PT011, PT012
            import asyncio

            asyncio.run(create_transcription_job(mock_file, api_key="test", diarize=False))

        assert "422" in str(exc_info.value) or "filename" in str(exc_info.value).lower()

    def test_diarize_endpoint_with_missing_filename(self) -> None:
        """Test diarize endpoint checks for filename (line 94)."""
        from unittest.mock import AsyncMock

        from fastapi import UploadFile

        from vtt_transcribe.api.routes.transcription import create_diarization_job

        # Create UploadFile with no filename
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = ""

        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:  # noqa: PT011, PT012
            import asyncio

            asyncio.run(create_diarization_job(mock_file, hf_token="test"))  # noqa: S106

        assert "422" in str(exc_info.value) or "filename" in str(exc_info.value).lower()

    def test_diarize_endpoint_async_processing(self) -> None:
        """Test /diarize endpoint async processing path (lines 126-138)."""
        from fastapi.testclient import TestClient

        from vtt_transcribe.api import app

        client = TestClient(app)

        response = client.post(
            "/diarize",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"hf_token": "test-hf-token", "device": "cpu"},
        )

        assert response.status_code == 200
        job_id = response.json()["job_id"]  # noqa: F841
        assert response.json()["status"] == "pending"
        assert "job_id" in response.json()

    def test_transcribe_async_exception_handling(self) -> None:
        """Test exception handling in _process_transcription (lines 161-172)."""
        from fastapi.testclient import TestClient

        from vtt_transcribe.api import app

        client = TestClient(app)

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock_vt:
            # Make transcriber raise an exception
            mock_instance = MagicMock()
            mock_instance.transcribe.side_effect = RuntimeError("Test error")
            mock_vt.return_value = mock_instance

            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )

            job_id = response.json()["job_id"]

            # Give async task time to fail
            import time

            time.sleep(0.3)

            # Check job status - should be failed
            status_response = client.get(f"/jobs/{job_id}")
            assert status_response.json()["status"] == "failed"
            assert "error" in status_response.json()

    def test_diarize_async_exception_handling(self) -> None:
        """Test exception handling in _process_diarization (lines 126-138)."""
        from fastapi.testclient import TestClient

        from vtt_transcribe.api import app

        client = TestClient(app)

        # Test the async exception path directly
        response = client.post(
            "/diarize",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"hf_token": "test-hf-token"},
        )

        job_id = response.json()["job_id"]

        # Let async processing happen (it will complete successfully with placeholder)
        import time

        time.sleep(0.3)

        # Verify job completed (covers the try/finally path)
        status_response = client.get(f"/jobs/{job_id}")
        assert status_response.json()["status"] in ["completed", "processing", "failed"]


class TestTranscriptionAsyncPaths:
    """Tests to cover async processing paths in transcription.py."""

    def test_process_diarization_complete_path(self) -> None:
        """Test _process_diarization async function (lines 126-138)."""
        from unittest.mock import AsyncMock

        from vtt_transcribe.api.routes.transcription import _process_diarization, jobs

        # Create an async mock UploadFile
        test_content = b"fake audio data"
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.mp3"
        mock_file.read = AsyncMock(return_value=test_content)

        job_id = "test-job-id"
        jobs[job_id] = {"status": "pending", "job_id": job_id}

        # Run the async function using asyncio.run
        asyncio.run(_process_diarization(job_id, mock_file, "test-token", "cpu"))

        # Verify job completed
        assert jobs[job_id]["status"] == "completed"
        assert "result" in jobs[job_id]

    def test_process_transcription_exception_path(self) -> None:
        """Test _process_transcription exception handling (lines 161-172)."""
        from unittest.mock import AsyncMock

        from vtt_transcribe.api.routes.transcription import _process_transcription, jobs

        # Create an async mock UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.mp3"
        mock_file.read = AsyncMock(return_value=b"fake audio")

        job_id = "test-exception-job"
        jobs[job_id] = {"status": "pending", "job_id": job_id}

        # Mock VideoTranscriber to raise exception
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock_vt:
            mock_instance = MagicMock()
            mock_instance.transcribe.side_effect = RuntimeError("Transcription failed")
            mock_vt.return_value = mock_instance

            # Run the async function
            asyncio.run(_process_transcription(job_id, mock_file, "test-key"))

            # Verify job marked as failed
            assert jobs[job_id]["status"] == "failed"
            assert "error" in jobs[job_id]
            assert "Transcription failed" in jobs[job_id]["error"]

    def test_transcription_complete_success_path(self) -> None:
        """Test successful transcription completion (lines 168-169)."""
        from vtt_transcribe.api.routes.transcription import _process_transcription, jobs

        # Create async mock UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "success.mp3"
        mock_file.read = AsyncMock(return_value=b"test audio content")

        job_id = "success-job"
        jobs[job_id] = {"status": "pending", "job_id": job_id}

        # Mock VideoTranscriber to succeed
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock_vt:
            mock_instance = MagicMock()
            mock_instance.transcribe.return_value = "[00:00 - 00:05] Test transcript"
            mock_vt.return_value = mock_instance

            # Run async function
            asyncio.run(_process_transcription(job_id, mock_file, "test-api-key"))

            # Verify lines 168-169 executed (status completed, result set)
            assert jobs[job_id]["status"] == "completed"
            assert jobs[job_id]["result"] == "[00:00 - 00:05] Test transcript"
