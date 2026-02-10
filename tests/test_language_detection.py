"""Tests for transcriber language detection."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vtt_transcribe.transcriber import VideoTranscriber


class TestLanguageDetection:
    """Test language detection in VideoTranscriber."""

    def test_detect_language_returns_language_code(self, tmp_path: Path) -> None:
        """Test that detect_language returns detected language code."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("vtt_transcribe.transcriber.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock the transcription response with language detection
            mock_response = MagicMock()
            mock_response.language = "es"  # Spanish
            mock_client.audio.transcriptions.create.return_value = mock_response

            transcriber = VideoTranscriber("test-api-key")
            result = transcriber.detect_language(audio_file)

            assert result == "es"
            mock_client.audio.transcriptions.create.assert_called_once()
            # Verify it requested verbose_json format for language detection
            call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
            assert call_kwargs["response_format"] == "verbose_json"

    def test_detect_language_file_not_found(self, tmp_path: Path) -> None:
        """Test that detect_language raises FileNotFoundError for missing file."""
        audio_file = tmp_path / "nonexistent.mp3"

        transcriber = VideoTranscriber("test-api-key")
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcriber.detect_language(audio_file)

    def test_detect_language_returns_unknown_if_no_language_attribute(self, tmp_path: Path) -> None:
        """Test that detect_language returns 'unknown' if response has no language."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("vtt_transcribe.transcriber.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock response without language attribute
            mock_response = MagicMock(spec=[])  # No attributes
            mock_client.audio.transcriptions.create.return_value = mock_response

            transcriber = VideoTranscriber("test-api-key")
            result = transcriber.detect_language(audio_file)

            assert result == "unknown"
