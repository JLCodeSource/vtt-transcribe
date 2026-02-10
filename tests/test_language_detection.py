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

    def test_detect_language_handles_dict_response(self, tmp_path: Path) -> None:
        """Test that detect_language handles dict-like responses."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("vtt_transcribe.transcriber.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock response as dict
            mock_response = {"language": "fr", "text": "Bonjour"}
            mock_client.audio.transcriptions.create.return_value = mock_response

            transcriber = VideoTranscriber("test-api-key")
            result = transcriber.detect_language(audio_file)

            assert result == "fr"

    def test_detect_language_handles_large_files(self, tmp_path: Path) -> None:
        """Test that detect_language extracts a chunk for large files."""
        # Create a file that appears to be > 25MB
        audio_file = tmp_path / "large.mp3"
        # Create a file with size > 25MB (26MB)
        audio_file.write_bytes(b"x" * (26 * 1024 * 1024))

        with (
            patch("vtt_transcribe.transcriber.OpenAI") as mock_openai,
            patch("vtt_transcribe.transcriber.AudioFileManager") as mock_manager,
        ):
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock the chunk extraction
            chunk_path = tmp_path / "large_chunk999999.mp3"
            chunk_path.write_bytes(b"small chunk content")
            mock_manager.get_duration.return_value = 120.0  # 2 minutes
            mock_manager.extract_chunk.return_value = chunk_path

            # Mock the language detection response
            mock_response = MagicMock()
            mock_response.language = "de"
            mock_client.audio.transcriptions.create.return_value = mock_response

            transcriber = VideoTranscriber("test-api-key")
            result = transcriber.detect_language(audio_file)

            assert result == "de"
            # Verify that chunk extraction was called for first 30 seconds
            mock_manager.extract_chunk.assert_called_once()
            call_args = mock_manager.extract_chunk.call_args
            assert call_args[0][1] == 0  # start_time
            assert call_args[0][2] == 30  # end_time (30 seconds)

    def test_detect_language_handles_chunking_failure(self, tmp_path: Path) -> None:
        """Test that detect_language falls back to full file if chunking fails."""
        # Create a file that appears to be > 25MB
        audio_file = tmp_path / "large.mp3"
        audio_file.write_bytes(b"x" * (26 * 1024 * 1024))

        with (
            patch("vtt_transcribe.transcriber.OpenAI") as mock_openai,
            patch("vtt_transcribe.transcriber.AudioFileManager") as mock_manager,
        ):
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock the chunk extraction to fail
            mock_manager.get_duration.side_effect = Exception("Duration extraction failed")

            # Mock the language detection response on full file
            mock_response = MagicMock()
            mock_response.language = "fr"
            mock_client.audio.transcriptions.create.return_value = mock_response

            transcriber = VideoTranscriber("test-api-key")
            result = transcriber.detect_language(audio_file)

            assert result == "fr"
            # Should have tried to get duration, but fallen back to full file
            mock_manager.get_duration.assert_called_once()
            # Should not have tried to extract chunk
            mock_manager.extract_chunk.assert_not_called()
