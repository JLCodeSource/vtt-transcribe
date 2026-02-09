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
