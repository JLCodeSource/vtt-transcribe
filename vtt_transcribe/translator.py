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
            transcript: Formatted transcript with timestamps [MM:SS - MM:SS] or [HH:MM:SS - HH:MM:SS] format
            target_language: Target language name (e.g., "Spanish", "French")
            preserve_timestamps: If True, preserve timestamp format in output

        Returns:
            Translated transcript with timestamps preserved
        """
        if not preserve_timestamps:
            # Simple translation of entire text
            return self.translate_text(transcript, target_language)

        # Split into lines and extract text portions for batch translation
        lines = transcript.strip().split("\n")
        line_info: list[tuple[str, str, str]] = []  # (original_line, timestamp, text_to_translate)
        
        for line in lines:
            line = line.strip()
            if not line:
                line_info.append((line, "", ""))
                continue

            # Check if line has timestamp format: [MM:SS - MM:SS] or [HH:MM:SS - HH:MM:SS]
            if line.startswith("[") and "]" in line:
                # Extract timestamp and text
                timestamp_end = line.index("]")
                timestamp = line[: timestamp_end + 1]
                remaining_text = line[timestamp_end + 1 :].strip()
                
                # Check for speaker label (SPEAKER_XX:)
                speaker_label = ""
                text_to_translate = remaining_text
                if remaining_text and ":" in remaining_text:
                    # Check if it matches speaker pattern
                    import re
                    speaker_match = re.match(r"^(SPEAKER_\d+:)\s*(.*)$", remaining_text)
                    if speaker_match:
                        speaker_label = speaker_match.group(1)
                        text_to_translate = speaker_match.group(2)

                line_info.append((line, timestamp, text_to_translate))
                # Store speaker label if present
                if speaker_label:
                    line_info[-1] = (line, timestamp, text_to_translate, speaker_label)  # type: ignore[assignment]
            else:
                # No timestamp, translate entire line
                line_info.append((line, "", line))

        # Batch translate all text portions
        texts_to_translate = [info[2] for info in line_info if info[2]]
        
        if not texts_to_translate:
            return transcript
        
        # Create a single batch request with all texts
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
        
        translated_batch = response.choices[0].message.content or ""
        
        # Parse the translated batch back into individual lines
        translated_texts: dict[int, str] = {}
        for line in translated_batch.split("\n"):
            line = line.strip()
            if line.startswith("LINE_"):
                try:
                    idx_end = line.index(":")
                    idx = int(line[5:idx_end])
                    text = line[idx_end + 1:].strip()
                    translated_texts[idx] = text
                except (ValueError, IndexError):
                    continue
        
        # Reconstruct the transcript with translated text
        translated_lines = []
        text_idx = 0
        
        for info in line_info:
            if not info[1]:  # No timestamp (empty line or plain text)
                if not info[0]:  # Empty line
                    translated_lines.append("")
                elif info[2]:  # Plain text to translate
                    translated_lines.append(translated_texts.get(text_idx, info[2]))
                    text_idx += 1
                else:
                    translated_lines.append(info[0])
            else:  # Has timestamp
                timestamp = info[1]
                if info[2]:  # Has text to translate
                    translated_text = translated_texts.get(text_idx, info[2])
                    text_idx += 1
                    # Check if we stored a speaker label
                    if len(info) > 3:  # Has speaker label
                        speaker_label = info[3]  # type: ignore[misc]
                        translated_lines.append(f"{timestamp} {speaker_label} {translated_text}")
                    else:
                        translated_lines.append(f"{timestamp} {translated_text}")
                else:
                    translated_lines.append(timestamp)

        return "\n".join(translated_lines)
