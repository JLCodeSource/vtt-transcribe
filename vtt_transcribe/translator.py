"""Audio translation functionality using OpenAI API."""

from pathlib import Path

from openai import OpenAI


class AudioTranslator:
    """Translate audio files and text using OpenAI's API."""

    def __init__(self, api_key: str) -> None:
        """Initialize translator with API key."""
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

    def translate_audio_file(self, audio_path: Path) -> str:
        """Translate audio file to English using OpenAI Whisper translations API.

        Args:
            audio_path: Path to audio file

        Returns:
            Translated text in English

        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        if not audio_path.exists():
            msg = f"Audio file not found: {audio_path}"
            raise FileNotFoundError(msg)

        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.translations.create(
                model="whisper-1",
                file=audio_file,
            )

        return response.text

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text to target language using OpenAI chat completions.

        Args:
            text: Text to translate
            target_language: Target language name (e.g., "Spanish", "French")

        Returns:
            Translated text
        """
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a translator. Translate the following text to {target_language}. "
                        "Return only the translation, no explanations."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )

        return response.choices[0].message.content or ""
