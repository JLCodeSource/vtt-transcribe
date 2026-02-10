"""Tests for translation functionality."""

from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from openai.types.audio.translation import Translation

from vtt_transcribe.translator import AudioTranslator


class TestAudioTranslator:
    """Test AudioTranslator class."""

    def test_initialization_with_api_key(self) -> None:
        """Test translator initialization with API key."""
        with patch("vtt_transcribe.translator.OpenAI"):
            translator = AudioTranslator("test-api-key")
            assert translator.api_key == "test-api-key"

    def test_translate_audio_file(self, tmp_path: Path) -> None:
        """Test translating an audio file to English."""
        # Create a fake audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("vtt_transcribe.translator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock the translation response
            mock_response = cast(
                "Translation",
                MagicMock(text="This is a translated transcript."),
            )
            mock_client.audio.translations.create.return_value = mock_response

            translator = AudioTranslator("test-api-key")
            result = translator.translate_audio_file(audio_file)

            assert result == "This is a translated transcript."
            mock_client.audio.translations.create.assert_called_once()

    def test_translate_audio_file_not_found(self) -> None:
        """Test translation raises FileNotFoundError for non-existent file."""
        with patch("vtt_transcribe.translator.OpenAI"):
            translator = AudioTranslator("test-api-key")

            with pytest.raises(FileNotFoundError, match="Audio file not found"):
                translator.translate_audio_file(Path("nonexistent.mp3"))

    def test_translate_text_using_chat_api(self) -> None:
        """Test translating text to a target language using chat completions."""
        with patch("vtt_transcribe.translator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock the chat completion response
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock(message=MagicMock(content="Ceci est un test."))]
            mock_client.chat.completions.create.return_value = mock_completion

            translator = AudioTranslator("test-api-key")
            result = translator.translate_text("This is a test.", target_language="French")

            assert result == "Ceci est un test."
            mock_client.chat.completions.create.assert_called_once()

    def test_translate_text_empty_response(self) -> None:
        """Test translation handles empty response from API."""
        with patch("vtt_transcribe.translator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock empty response
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock(message=MagicMock(content=""))]
            mock_client.chat.completions.create.return_value = mock_completion

            translator = AudioTranslator("test-api-key")
            result = translator.translate_text("Test text", target_language="Spanish")

            assert result == ""

    def test_translate_transcript_with_timestamps(self) -> None:
        """Test translating formatted transcript while preserving timestamps."""
        transcript = "[00:00 - 00:05] Hello, how are you?\n[00:05 - 00:10] I am doing well, thanks."

        with patch("vtt_transcribe.translator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock chat completion responses for each segment
            mock_resp1 = MagicMock()
            mock_resp1.choices = [MagicMock(message=MagicMock(content="Hola, ¿cómo estás?"))]
            mock_resp2 = MagicMock()
            mock_resp2.choices = [MagicMock(message=MagicMock(content="Estoy bien, gracias."))]
            mock_client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]

            translator = AudioTranslator("test-api-key")
            result = translator.translate_transcript(transcript, "Spanish", preserve_timestamps=True)

            assert "[00:00 - 00:05] Hola, ¿cómo estás?" in result
            assert "[00:05 - 00:10] Estoy bien, gracias." in result
            assert mock_client.chat.completions.create.call_count == 2

    def test_translate_transcript_without_timestamps(self) -> None:
        """Test translating entire transcript without preserving format."""
        transcript = "[00:00 - 00:05] Hello, how are you?\n[00:05 - 00:10] I am doing well."

        with patch("vtt_transcribe.translator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock chat completion response
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock(message=MagicMock(content="Hola, ¿cómo estás? Estoy bien."))]
            mock_client.chat.completions.create.return_value = mock_resp

            translator = AudioTranslator("test-api-key")
            result = translator.translate_transcript(transcript, "Spanish", preserve_timestamps=False)

            assert result == "Hola, ¿cómo estás? Estoy bien."
            mock_client.chat.completions.create.assert_called_once()

    def test_translate_transcript_empty_lines(self) -> None:
        """Test translating transcript with empty lines."""
        transcript = "[00:00 - 00:05] Hello\n\n[00:10 - 00:15] World"

        with patch("vtt_transcribe.translator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock responses
            mock_resp1 = MagicMock()
            mock_resp1.choices = [MagicMock(message=MagicMock(content="Hola"))]
            mock_resp2 = MagicMock()
            mock_resp2.choices = [MagicMock(message=MagicMock(content="Mundo"))]
            mock_client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]

            translator = AudioTranslator("test-api-key")
            result = translator.translate_transcript(transcript, "Spanish", preserve_timestamps=True)

            lines = result.split("\n")
            assert "[00:00 - 00:05] Hola" in result
            assert "[00:10 - 00:15] Mundo" in result
            # Should preserve empty line
            assert "" in lines
