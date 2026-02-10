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

    def _parse_line_for_translation(self, line: str) -> tuple[str, str, str] | tuple[str, str, str, str]:
        """Parse a line to extract timestamp and text for translation.

        Returns:
            Tuple of (original_line, timestamp, text_to_translate) or
            (original_line, timestamp, text_to_translate, speaker_label)
        """
        line = line.strip()
        if not line:
            return (line, "", "")

        # Check if line has timestamp format
        if line.startswith("[") and "]" in line:
            timestamp_end = line.index("]")
            timestamp = line[: timestamp_end + 1]
            remaining_text = line[timestamp_end + 1 :].strip()

            # Check for speaker label
            if remaining_text and ":" in remaining_text:
                import re

                speaker_match = re.match(r"^(SPEAKER_\d+:)\s*(.*)$", remaining_text)
                if speaker_match:
                    return (line, timestamp, speaker_match.group(2), speaker_match.group(1))

            return (line, timestamp, remaining_text)

        # No timestamp
        return (line, "", line)

    def _parse_translated_batch(self, translated_batch: str) -> dict[int, str]:
        """Parse batch translation response into indexed dictionary."""
        translated_texts: dict[int, str] = {}
        for line in translated_batch.split("\n"):
            line = line.strip()
            if line.startswith("LINE_"):
                try:
                    idx_end = line.index(":")
                    idx = int(line[5:idx_end])
                    text = line[idx_end + 1 :].strip()
                    translated_texts[idx] = text
                except (ValueError, IndexError):
                    continue
        return translated_texts

    def _reconstruct_line(
        self, info: tuple[str, str, str] | tuple[str, str, str, str], translated_texts: dict[int, str], text_idx: int
    ) -> tuple[str, int]:
        """Reconstruct a single line with translation.

        Returns:
            Tuple of (reconstructed_line, new_text_idx)
        """
        if not info[1]:  # No timestamp
            if not info[0]:  # Empty line
                return ("", text_idx)
            if info[2]:  # Plain text to translate
                return (translated_texts.get(text_idx, info[2]), text_idx + 1)
            return (info[0], text_idx)

        # Has timestamp
        timestamp = info[1]
        if not info[2]:  # No text to translate
            return (timestamp, text_idx)

        # Has text to translate
        translated_text = translated_texts.get(text_idx, info[2])
        text_idx += 1

        if len(info) > 3:  # Has speaker label
            speaker_label = info[3]
            return (f"{timestamp} {speaker_label} {translated_text}", text_idx)

        return (f"{timestamp} {translated_text}", text_idx)

    def translate_transcript(self, transcript: str, target_language: str, *, preserve_timestamps: bool = True) -> str:
        """Translate a formatted transcript while preserving timestamps.

        Args:
            transcript: Formatted transcript with timestamps [MM:SS - MM:SS] or [HH:MM:SS - HH:MM:SS] format
            target_language: Target language name (e.g., "Spanish", "French")
            preserve_timestamps: If True, preserve timestamp format in output

        Returns:
            Translated transcript with timestamps preserved
        """
        if not preserve_timestamps:
            return self.translate_text(transcript, target_language)

        # Parse lines and extract text for translation
        lines = transcript.strip().split("\n")
        line_info = [self._parse_line_for_translation(line) for line in lines]

        # Batch translate all text portions
        texts_to_translate = [info[2] for info in line_info if info[2]]
        if not texts_to_translate:
            return transcript

        # Create batch request
        batch_text = "\n".join(f"LINE_{i}: {text}" for i, text in enumerate(texts_to_translate))
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a translator. Translate each line to {target_language}. "
                        "Keep each line separate and preserve the LINE_N: prefix for each line. "
                        "Return only the translations with their LINE_N: prefixes, no explanations."
                    ),
                },
                {"role": "user", "content": batch_text},
            ],
        )

        # Parse translation results
        translated_batch = response.choices[0].message.content or ""
        translated_texts = self._parse_translated_batch(translated_batch)

        # Reconstruct transcript with translations
        translated_lines = []
        text_idx = 0
        for info in line_info:
            reconstructed, text_idx = self._reconstruct_line(info, translated_texts, text_idx)
            translated_lines.append(reconstructed)

        return "\n".join(translated_lines)
