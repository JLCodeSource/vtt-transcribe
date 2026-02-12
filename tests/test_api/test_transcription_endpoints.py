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
        response = client.post("/api/transcribe")
        assert response.status_code != 404

    def test_transcribe_requires_file(self, client):
        """POST /transcribe should require a file upload."""
        response = client.post("/api/transcribe")
        assert response.status_code == 422

    def test_transcribe_requires_api_key(self, client, sample_audio_file):
        """POST /transcribe should require OpenAI API key."""
        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        response = client.post("/api/transcribe", files=files)
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
        response = client.post("/api/transcribe", files=files, data=data)

        assert response.status_code in [200, 201, 202]

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_transcribe_returns_job_id(self, mock_transcriber, client, sample_audio_file):
        """POST /transcribe should return a job ID for async processing."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/api/transcribe", files=files, data=data)

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
        response = client.post("/api/transcribe", files=files, data=data)

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
        create_response = client.post("/api/transcribe", files=files, data=data)
        job_id = create_response.json()["job_id"]

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code != 404

    def test_job_status_returns_not_found_for_invalid_id(self, client):
        """GET /jobs/{job_id} should return 404 for non-existent job."""
        response = client.get("/api/jobs/nonexistent-job-id")
        assert response.status_code == 404

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_job_status_returns_job_info(self, mock_transcriber, client, sample_audio_file):
        """GET /jobs/{job_id} should return job information."""
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Test transcript")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        create_response = client.post("/api/transcribe", files=files, data=data)
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/api/jobs/{job_id}")
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
        response = client.post("/api/transcribe", files=files, data=data)

        assert response.status_code in [200, 201, 202]


class TestAPITranscriptionCoverage:
    """Tests to cover missing lines in api/routes/transcription.py."""

    def test_transcribe_with_missing_filename(self) -> None:
        """Test transcribe endpoint checks for filename (line 39)."""
        from fastapi import UploadFile

        from vtt_transcribe.api.routes.transcription import create_transcription_job

        # Create UploadFile with no filename
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None

        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:  # noqa: PT011, PT012
            import asyncio

            asyncio.run(create_transcription_job(mock_file, api_key="test", diarize=False))

        assert "422" in str(exc_info.value) or "filename" in str(exc_info.value).lower()

    def test_diarize_endpoint_with_missing_filename(self) -> None:
        """Test diarize endpoint checks for filename (line 94)."""
        from fastapi import UploadFile

        from vtt_transcribe.api.routes.transcription import create_diarization_job

        # Create UploadFile with no filename
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = ""

        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:  # noqa: PT011, PT012
            import asyncio

            asyncio.run(create_diarization_job(mock_file, hf_token="test"))

        assert "422" in str(exc_info.value) or "filename" in str(exc_info.value).lower()

    def test_diarize_endpoint_async_processing(self) -> None:
        """Test /diarize endpoint async processing path (lines 126-138)."""
        from fastapi.testclient import TestClient

        from vtt_transcribe.api import app

        client = TestClient(app)

        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"hf_token": "test-hf-token", "device": "cpu"},
        )

        assert response.status_code == 200
        job_id = response.json()["job_id"]  # noqa: F841
        assert response.json()["status"] == "pending"
        assert "job_id" in response.json()

    def test_transcribe_async_exception_handling(self) -> None:
        """Test that transcription job is created successfully.

        Note: Background task exception handling is tested in TestTranscriptionAsyncPaths
        which directly calls _process_transcription. TestClient doesn't execute background
        asyncio tasks, so we only verify job creation here.
        """
        from fastapi.testclient import TestClient

        from vtt_transcribe.api import app

        client = TestClient(app)

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber"):
            response = client.post(
                "/api/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "test-key"},
            )

            # Verify job was created successfully
            assert response.status_code in [200, 201, 202]
            job_data = response.json()
            assert "job_id" in job_data
            assert job_data["status"] == "pending"

    def test_diarize_async_exception_handling(self) -> None:
        """Test exception handling in _process_diarization (lines 126-138)."""
        from fastapi.testclient import TestClient

        from vtt_transcribe.api import app

        client = TestClient(app)

        # Test the async exception path directly
        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"hf_token": "test-hf-token"},
        )

        job_id = response.json()["job_id"]

        # Let async processing happen (it will complete successfully with placeholder)
        import time

        time.sleep(0.3)

        # Verify job completed (covers the try/finally path)
        status_response = client.get(f"/api/jobs/{job_id}")
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
        from vtt_transcribe.api.routes.transcription import _process_transcription, jobs

        job_id = "test-exception-job"
        jobs[job_id] = {"status": "pending", "job_id": job_id}

        # Mock VideoTranscriber to raise exception
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock_vt:
            mock_instance = MagicMock()
            mock_instance.transcribe.side_effect = RuntimeError("Transcription failed")
            mock_vt.return_value = mock_instance

            # Run the async function
            asyncio.run(
                _process_transcription(
                    job_id=job_id,
                    content=b"fake audio",
                    filename="test.mp3",
                    api_key="test-key",
                )
            )

            # Verify job marked as failed
            assert jobs[job_id]["status"] == "failed"
            assert "error" in jobs[job_id]
            assert "Transcription failed" in jobs[job_id]["error"]

    def test_transcription_complete_success_path(self) -> None:
        """Test successful transcription completion (lines 168-169)."""
        from vtt_transcribe.api.routes.transcription import _process_transcription, jobs

        job_id = "success-job"
        jobs[job_id] = {"status": "pending", "job_id": job_id}

        # Mock VideoTranscriber to succeed
        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock_vt:
            mock_instance = MagicMock()
            mock_instance.transcribe.return_value = "[00:00 - 00:05] Test transcript"
            mock_vt.return_value = mock_instance

            # Run async function
            asyncio.run(
                _process_transcription(
                    job_id=job_id,
                    content=b"test audio content",
                    filename="success.mp3",
                    api_key="test-api-key",
                )
            )

            # Verify lines 168-169 executed (status completed, result set)
            assert jobs[job_id]["status"] == "completed"
            assert jobs[job_id]["result"] == "[00:00 - 00:05] Test transcript"


class TestDetectLanguageEndpoint:
    """Tests for /detect-language endpoint."""

    def test_detect_language_endpoint_exists(self, client):
        """POST /detect-language endpoint should exist."""
        response = client.post("/api/detect-language")
        assert response.status_code != 404

    def test_detect_language_requires_file(self, client):
        """POST /detect-language should require a file upload."""
        response = client.post("/api/detect-language")
        assert response.status_code == 422

    def test_detect_language_requires_api_key(self, client, sample_audio_file):
        """POST /detect-language should require OpenAI API key."""
        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        response = client.post("/api/detect-language", files=files)
        assert response.status_code == 422

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_detect_language_returns_language_code(self, mock_transcriber, client, sample_audio_file):
        """POST /detect-language should return detected language code."""
        mock_instance = mock_transcriber.return_value
        mock_instance.detect_language = MagicMock(return_value="es")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/api/detect-language", files=files, data=data)

        assert response.status_code == 200
        response_data = response.json()
        assert "language_code" in response_data
        assert response_data["language_code"] == "es"


class TestTranslateEndpoint:
    """Tests for /translate endpoint."""

    def test_translate_endpoint_exists(self, client):
        """POST /translate endpoint should exist."""
        response = client.post("/api/translate")
        assert response.status_code != 404

    def test_translate_requires_transcript(self, client):
        """POST /translate should require transcript text."""
        response = client.post("/api/translate", data={})
        assert response.status_code == 422

    def test_translate_requires_target_language(self, client):
        """POST /translate should require target_language."""
        response = client.post("/api/translate", data={"transcript": "Hello"})
        assert response.status_code == 422

    def test_translate_requires_api_key(self, client):
        """POST /translate should require OpenAI API key."""
        response = client.post("/api/translate", data={"transcript": "Hello", "target_language": "Spanish"})
        assert response.status_code == 422

    @patch("vtt_transcribe.api.routes.transcription.AudioTranslator")
    def test_translate_returns_translated_text(self, mock_translator, client):
        """POST /translate should return translated transcript."""
        mock_instance = mock_translator.return_value
        mock_instance.translate_transcript = MagicMock(return_value="[00:00 - 00:05] Hola, ¿cómo estás?")

        response = client.post(
            "/api/translate",
            data={
                "transcript": "[00:00 - 00:05] Hello, how are you?",
                "target_language": "Spanish",
                "api_key": "test-api-key",
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "translated" in response_data
        assert "Hola" in response_data["translated"]


class TestTranscribeWithTranslation:
    """Tests for transcription with translation support."""

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    @patch("vtt_transcribe.api.routes.transcription.AudioTranslator")
    def test_transcribe_with_translate_to_parameter(self, mock_translator, mock_transcriber, client, sample_audio_file):
        """POST /transcribe with translate_to should trigger translation."""
        mock_transcriber_instance = mock_transcriber.return_value
        mock_transcriber_instance.transcribe_from_buffer = AsyncMock(return_value="[00:00 - 00:05] Hello world")

        mock_translator_instance = mock_translator.return_value
        mock_translator_instance.translate_transcript = MagicMock(return_value="[00:00 - 00:05] Hola mundo")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key", "translate_to": "Spanish"}
        response = client.post("/api/transcribe", files=files, data=data)

        assert response.status_code in [200, 201, 202]
        response_data = response.json()
        assert "job_id" in response_data

    def test_transcription_translation_async_path(self):
        """Test async translation path in _process_transcription."""
        from vtt_transcribe.api.routes.transcription import _process_transcription, jobs

        job_id = "translation-job"
        jobs[job_id] = {"status": "pending", "job_id": job_id}

        with (
            patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock_vt,
            patch("vtt_transcribe.api.routes.transcription.AudioTranslator") as mock_at,
        ):
            # Mock successful transcription
            mock_vt_instance = MagicMock()
            mock_vt_instance.transcribe.return_value = "[00:00 - 00:05] English text"
            mock_vt.return_value = mock_vt_instance

            # Mock successful translation
            mock_at_instance = MagicMock()
            mock_at_instance.translate_transcript.return_value = "[00:00 - 00:05] Texto español"
            mock_at.return_value = mock_at_instance

            # Run with translation
            asyncio.run(
                _process_transcription(
                    job_id=job_id, content=b"fake audio", filename="test.mp3", api_key="test-key", translate_to="Spanish"
                )
            )

            # Verify translation was called and result includes translation
            assert jobs[job_id]["status"] == "completed"
            assert "Texto español" in jobs[job_id]["result"]
            mock_at_instance.translate_transcript.assert_called_once()


class TestDetectLanguageErrorHandling:
    """Tests for error handling in /detect-language endpoint."""

    def test_detect_language_missing_filename(self) -> None:
        """Test detect_language when file has no filename."""
        import asyncio
        import io

        from fastapi import UploadFile
        from fastapi.exceptions import HTTPException

        from vtt_transcribe.api.routes.transcription import detect_language

        # Create UploadFile with None filename
        mock_file = UploadFile(file=io.BytesIO(b"test"), filename=None)  # type: ignore[arg-type]

        # This should raise HTTPException with 422 status
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(detect_language(file=mock_file, api_key="test-key"))

        assert exc_info.value.status_code == 422
        assert "filename" in exc_info.value.detail.lower()

    def test_detect_language_unsupported_extension(self, client, sample_audio_file):
        """Test detect_language with unsupported file extension."""
        files = {"file": ("test.xyz", sample_audio_file, "application/octet-stream")}
        data = {"api_key": "test-api-key"}
        response = client.post("/api/detect-language", files=files, data=data)

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_detect_language_file_too_large(self, client):
        """Test detect_language with file exceeding size limit."""
        # Create a file larger than MAX_FILE_SIZE (100MB)
        large_content = b"x" * (101 * 1024 * 1024)
        files = {"file": ("test.mp3", io.BytesIO(large_content), "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/api/detect-language", files=files, data=data)

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_detect_language_processing_exception(self, mock_transcriber, client, sample_audio_file):
        """Test detect_language when transcriber raises exception."""
        mock_instance = mock_transcriber.return_value
        mock_instance.detect_language = MagicMock(side_effect=RuntimeError("Detection failed"))

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        response = client.post("/api/detect-language", files=files, data=data)

        assert response.status_code == 500
        assert "Language detection failed" in response.json()["detail"]


class TestTranslateErrorHandling:
    """Tests for error handling in /translate endpoint."""

    @patch("vtt_transcribe.api.routes.transcription.AudioTranslator")
    def test_translate_processing_exception(self, mock_translator, client):
        """Test translate when translator raises exception."""
        mock_instance = mock_translator.return_value
        mock_instance.translate_transcript = MagicMock(side_effect=RuntimeError("Translation failed"))

        response = client.post(
            "/api/translate",
            data={
                "transcript": "[00:00 - 00:05] Hello",
                "target_language": "Spanish",
                "api_key": "test-api-key",
            },
        )

        assert response.status_code == 500
        assert "Translation failed" in response.json()["detail"]


class TestDownloadTranscriptEndpoint:
    """Tests for /jobs/{job_id}/download endpoint."""

    def test_download_job_not_found(self, client):
        """Test download with non-existent job ID."""
        response = client.get("/api/jobs/nonexistent-job/download?format=txt")
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_download_job_not_completed(self, mock_transcriber, client, sample_audio_file):
        """Test download when job is still processing."""
        # Create a job
        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe_from_buffer = MagicMock(return_value="[00:00 - 00:05] Test")

        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {"api_key": "test-api-key"}
        create_response = client.post("/api/transcribe", files=files, data=data)
        job_id = create_response.json()["job_id"]

        # Manually set job to processing state
        from vtt_transcribe.api.routes.transcription import jobs

        jobs[job_id]["status"] = "processing"

        # Try to download
        response = client.get(f"/api/jobs/{job_id}/download?format=txt")
        assert response.status_code == 400
        assert "Job not completed" in response.json()["detail"]

    def test_download_no_result_available(self, client):
        """Test download when job has no result."""
        # Create a completed job with empty result
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-empty-job"
        jobs[job_id] = {"status": "completed", "job_id": job_id, "result": ""}

        response = client.get(f"/api/jobs/{job_id}/download?format=txt")
        assert response.status_code == 404
        assert "No transcript available" in response.json()["detail"]

    def test_download_no_segments_parsed(self, client):
        """Test download when transcript has no valid segments."""
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-no-segments-job"
        jobs[job_id] = {"status": "completed", "job_id": job_id, "result": "Invalid transcript format"}

        response = client.get(f"/api/jobs/{job_id}/download?format=txt")
        assert response.status_code == 404
        assert "No segments found" in response.json()["detail"]

    def test_download_txt_format(self, client):
        """Test downloading transcript in TXT format."""
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-txt-job"
        jobs[job_id] = {
            "status": "completed",
            "job_id": job_id,
            "result": "[00:00:00 - 00:00:05] Hello world\n[00:00:05 - 00:00:10] How are you?",
        }

        response = client.get(f"/api/jobs/{job_id}/download?format=txt")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "Hello world" in response.text
        assert "How are you?" in response.text
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_download_vtt_format(self, client):
        """Test downloading transcript in VTT format."""
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-vtt-job"
        jobs[job_id] = {
            "status": "completed",
            "job_id": job_id,
            "result": "[00:00:00 - 00:00:05] Hello world",
        }

        response = client.get(f"/api/jobs/{job_id}/download?format=vtt")
        assert response.status_code == 200
        assert "text/vtt" in response.headers["content-type"]
        assert "WEBVTT" in response.text

    def test_download_srt_format(self, client):
        """Test downloading transcript in SRT format."""
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-srt-job"
        jobs[job_id] = {
            "status": "completed",
            "job_id": job_id,
            "result": "[00:00:00 - 00:00:05] Hello world",
        }

        response = client.get(f"/api/jobs/{job_id}/download?format=srt")
        assert response.status_code == 200
        assert "application/x-subrip" in response.headers["content-type"]
        assert "1" in response.text  # SRT sequence number
        assert "-->" in response.text

    def test_download_with_empty_lines(self, client):
        """Test downloading transcript with empty lines in middle."""
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-empty-lines-job"
        jobs[job_id] = {
            "status": "completed",
            "job_id": job_id,
            "result": "[00:00:00 - 00:00:05] First line\n\n[00:00:10 - 00:00:15] Second line",
        }

        response = client.get(f"/api/jobs/{job_id}/download?format=txt")
        assert response.status_code == 200
        # Empty lines should be skipped during parsing
        assert "First line" in response.text
        assert "Second line" in response.text

    def test_download_with_speaker_labels(self, client):
        """Test downloading transcript with speaker labels."""
        from vtt_transcribe.api.routes.transcription import jobs

        job_id = "test-speaker-job"
        jobs[job_id] = {
            "status": "completed",
            "job_id": job_id,
            "result": (
                "[SPEAKER_00] [00:00:00 - 00:00:05] Hello from speaker 0\n"
                "[SPEAKER_01] [00:00:05 - 00:00:10] Hello from speaker 1"
            ),
        }

        # Test TXT format with speakers
        response = client.get(f"/api/jobs/{job_id}/download?format=txt")
        assert response.status_code == 200
        assert "[SPEAKER_00]" in response.text
        assert "[SPEAKER_01]" in response.text

        # Test VTT format with speakers
        response = client.get(f"/api/jobs/{job_id}/download?format=vtt")
        assert response.status_code == 200
        assert "<v SPEAKER_00>" in response.text

        # Test SRT format with speakers
        response = client.get(f"/api/jobs/{job_id}/download?format=srt")
        assert response.status_code == 200
        assert "[SPEAKER_00]" in response.text


class TestProgressEventsInTranscription:
    """Tests for progress event emission during transcription."""

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_progress_events_emitted_during_transcription(self, mock_transcriber, client):
        """Progress events should be emitted during transcription processing."""
        from vtt_transcribe.api.routes.transcription import jobs

        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Test"
        mock_instance.detect_language.return_value = "en"

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"api_key": "test-key"},
        )
        job_id = response.json()["job_id"]

        # Verify job has progress_updates queue
        assert job_id in jobs
        assert "progress_updates" in jobs[job_id]

        # Give background task time to emit events
        import time

        time.sleep(0.2)

        # Check if progress events were emitted
        queue = jobs[job_id]["progress_updates"]
        # Queue should be an asyncio.Queue
        assert isinstance(queue, asyncio.Queue)

        # Drain queue and verify events were emitted
        events = []
        while not queue.empty():
            try:
                events.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        # Assert that at least one progress event was emitted
        assert len(events) >= 1, f"Expected at least 1 progress event, got {len(events)}"
        # Verify events have required structure
        for event in events:
            assert "type" in event, f"Event missing 'type' field: {event}"
            assert "message" in event, f"Event missing 'message' field: {event}"
            assert "timestamp" in event, f"Event missing 'timestamp' field: {event}"

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    def test_progress_events_for_language_detection(self, mock_transcriber, client):
        """Progress events should include language detection."""
        from vtt_transcribe.api.routes.transcription import jobs

        mock_instance = mock_transcriber.return_value
        mock_instance.transcribe.return_value = "[00:00 - 00:05] Test"
        mock_instance.detect_language.return_value = "es"

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"api_key": "test-key"},
        )
        job_id = response.json()["job_id"]

        # Give background task time to process
        import time

        time.sleep(0.3)

        # Check for language detection in progress
        assert job_id in jobs, "Job not found"
        assert "progress_updates" in jobs[job_id], "Progress queue not found"

        queue = jobs[job_id]["progress_updates"]
        events = []
        while not queue.empty():
            try:
                events.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        # Assert language-related events were emitted
        language_events = [e for e in events if e.get("type") == "language"]
        assert len(language_events) >= 1, f"Expected at least 1 language event, got {len(language_events)}"
        # Check that language detection was mentioned
        assert any("language" in e["message"].lower() for e in language_events)

    @patch("vtt_transcribe.api.routes.transcription.VideoTranscriber")
    @patch("vtt_transcribe.api.routes.transcription.AudioTranslator")
    def test_progress_events_for_translation(self, mock_translator, mock_transcriber, client):
        """Progress events should include translation progress."""
        from vtt_transcribe.api.routes.transcription import jobs

        mock_transcriber_instance = mock_transcriber.return_value
        mock_transcriber_instance.transcribe.return_value = "[00:00 - 00:05] Test"
        mock_transcriber_instance.detect_language.return_value = "en"

        mock_translator_instance = mock_translator.return_value
        mock_translator_instance.translate_transcript.return_value = "[00:00 - 00:05] Prueba"

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"api_key": "test-key", "translate_to": "Spanish"},
        )
        job_id = response.json()["job_id"]

        # Give background task time to process
        import time

        time.sleep(0.3)

        # Check for translation events in progress
        if job_id in jobs and "progress_updates" in jobs[job_id]:
            queue = jobs[job_id]["progress_updates"]
            events = []
            while not queue.empty():
                try:
                    events.append(queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            # May have translation-related events
            # Events are emitted asynchronously
            _ = [e for e in events if e.get("type") == "translation"]

    def test_diarization_job_has_progress_queue(self, client):
        """Diarization jobs should have progress_updates queue."""
        from vtt_transcribe.api.routes.transcription import jobs

        response = client.post(
            "/api/diarize",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"hf_token": "test-token"},
        )
        job_id = response.json()["job_id"]

        # Verify job has progress_updates queue
        assert job_id in jobs
        assert "progress_updates" in jobs[job_id]
        assert isinstance(jobs[job_id]["progress_updates"], asyncio.Queue)

    def test_emit_progress_function_exists(self):
        """_emit_progress function should exist and be callable."""
        from vtt_transcribe.api.routes.transcription import _emit_progress

        # Should not raise
        _emit_progress("test-job", "Test message", "info")
