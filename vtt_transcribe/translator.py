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

    def translate_transcript(self, transcript: str, target_language: str, *, preserve_timestamps: bool = True) -> str:
        """Translate a formatted transcript while preserving timestamps.

        Args:
            transcript: Formatted transcript with timestamps [MM:SS - MM:SS] text
            target_language: Target language name (e.g., "Spanish", "French")
            preserve_timestamps: If True, preserve timestamp format in output

        Returns:
            Translated transcript with timestamps preserved
        """
        if not preserve_timestamps:
            # Simple translation of entire text
            return self.translate_text(transcript, target_language)

        # Split into lines and translate each segment separately
        lines = transcript.strip().split("\n")
        translated_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                translated_lines.append("")
                continue

            # Check if line has timestamp format: [MM:SS - MM:SS] text
            if line.startswith("[") and "]" in line:
                # Extract timestamp and text
                timestamp_end = line.index("]")
                timestamp = line[: timestamp_end + 1]
                text = line[timestamp_end + 1 :].strip()

                if text:
                    # Translate just the text portion
                    translated_text = self.translate_text(text, target_language)
                    translated_lines.append(f"{timestamp} {translated_text}")
                else:
                    translated_lines.append(timestamp)
            else:
                # No timestamp, translate entire line
                translated_lines.append(self.translate_text(line, target_language))

        return "\n".join(translated_lines)
