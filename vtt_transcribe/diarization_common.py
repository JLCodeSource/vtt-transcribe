"""Backend-independent diarization helpers (no torch / pyannote / sherpa imports).

Holds the transcript-labelling logic and the file-handling wrapper shared by every diarization
backend, plus the pure formatting helpers. Backends subclass :class:`SpeakerLabeler` and implement
``_diarize_audio_internal``.

Timestamp Format:
    The primary timestamp format used throughout this module is HH:MM:SS (hours:minutes:seconds).
    This aligns with the TranscriptFormatter output format. Some functions maintain backward
    compatibility with the legacy MM:SS format for parsing existing transcripts.
"""

import re
import sys
import time
from pathlib import Path

from vtt_transcribe.logging_config import get_logger

# Same name as the historical logger so existing log filters and tests keep working.
logger = get_logger("vtt_transcribe.diarization")

# Default sample rate used by pyannote.audio v3.x
PYANNOTE_DEFAULT_SAMPLE_RATE = 44100


class SpeakerLabeler:
    """Shared behaviour for diarizers: run on a file (with WAV fallback) and label transcripts."""

    device: str

    def _diarize_audio_internal(self, audio_path: Path) -> list[tuple[float, float, str]]:
        """Backend-specific diarization. Returns (start, end, speaker_label) tuples."""
        raise NotImplementedError

    def diarize_audio(self, audio_path: Path) -> list[tuple[float, float, str]]:
        """Run speaker diarization on an audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            List of (start_time, end_time, speaker_label) tuples in seconds.

        Raises:
            ValueError: If audio file is too short (less than 10 seconds required).

        Note:
            The pyannote.audio model requires audio files to be at least 10 seconds long.
            For shorter audio files, consider padding with silence or using a different model.

            If MP3 encoding causes sample mismatch errors, the audio will be automatically
            converted to WAV format for more reliable processing.
        """
        start_time = time.time()

        # Get file size if file exists (for logging)
        try:
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        except (FileNotFoundError, OSError):
            file_size_mb = 0.0

        logger.info(
            "Starting audio diarization",
            extra={
                "audio_path": str(audio_path),
                "size_mb": round(file_size_mb, 2),
                "device": self.device,
            },
        )

        result = self._diarize_with_fallback(audio_path)

        duration = time.time() - start_time
        logger.info(
            "Audio diarization complete",
            extra={
                "duration_seconds": round(duration, 2),
                "num_segments": len(result),
                "num_speakers": len({seg[2] for seg in result}),
            },
        )

        return result

    def _diarize_with_fallback(self, audio_path: Path) -> list[tuple[float, float, str]]:
        """Try diarization, falling back to WAV conversion if MP3 has sample mismatch."""
        try:
            return self._diarize_audio_internal(audio_path)
        except ValueError as e:
            error_str = str(e)
            # Check if it's an MP3 sample mismatch that we can fix
            if "MP3 encoding imprecision" in error_str:
                print(
                    "\nMP3 encoding issue detected. Converting to WAV for more reliable processing...",
                    file=sys.stderr,
                )
                # Convert to WAV and retry
                wav_path = audio_path.with_suffix(".wav")
                try:
                    self._convert_to_wav(audio_path, wav_path)
                    result = self._diarize_audio_internal(wav_path)
                    # Clean up WAV file
                    wav_path.unlink()
                    return result
                except Exception as wav_error:
                    # Clean up WAV file if it exists
                    if wav_path.exists():
                        wav_path.unlink()
                    raise wav_error from e
            # Not a fixable MP3 issue, re-raise
            raise

    def _convert_to_wav(self, input_path: Path, output_path: Path) -> None:
        """Convert audio file to WAV format using ffmpeg."""
        import subprocess

        logger.info(
            "Converting audio to WAV format",
            extra={
                "input_path": str(input_path),
                "output_path": str(output_path),
            },
        )

        cmd = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",  # Overwrite output file
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
        if result.returncode != 0:
            logger.error(
                "WAV conversion failed",
                extra={"error": result.stderr},
            )
            msg = f"Failed to convert to WAV: {result.stderr}"
            raise RuntimeError(msg)

        logger.info("WAV conversion successful")

    def apply_speakers_to_transcript(
        self,
        transcript: str,
        speaker_segments: list[tuple[float, float, str]],
    ) -> str:
        """Apply speaker labels to timestamped transcript.

        Args:
            transcript: Transcript with [HH:MM:SS - HH:MM:SS] text format.
            speaker_segments: List of (start_time, end_time, speaker_label) tuples.

        Returns:
            Transcript with speaker labels: [HH:MM:SS - HH:MM:SS] Speaker: text
        """
        start_time = time.time()

        logger.info(
            "Starting speaker label application",
            extra={
                "transcript_length": len(transcript),
                "num_segments": len(speaker_segments),
                "num_speakers": len({seg[2] for seg in speaker_segments}) if speaker_segments else 0,
            },
        )

        if not speaker_segments:
            duration = time.time() - start_time
            logger.warning("No speaker segments provided, returning original transcript")
            logger.info(
                "Speaker label application complete",
                extra={
                    "duration_seconds": round(duration, 2),
                    "lines_processed": transcript.count("\n") + 1 if transcript else 0,
                    "result_length": len(transcript),
                },
            )
            return transcript

        lines = transcript.split("\n")
        labeled_lines = [self._process_line(line, speaker_segments) for line in lines]
        result = "\n".join(labeled_lines)

        duration = time.time() - start_time
        logger.info(
            "Speaker label application complete",
            extra={
                "duration_seconds": round(duration, 2),
                "lines_processed": len(lines),
                "result_length": len(result),
            },
        )

        return result

    def _process_line(self, line: str, speaker_segments: list[tuple[float, float, str]]) -> str:
        """Process a single transcript line and add speaker label if applicable.

        Args:
            line: Single line from transcript.
            speaker_segments: List of (start_time, end_time, speaker_label) tuples.

        Returns:
            Line with speaker label added, or original line if no match.
        """
        # Match timestamp pattern [HH:MM:SS - HH:MM:SS] or [MM:SS - MM:SS]
        match = re.match(r"\[(\d{2}):(\d{2}):(\d{2}) - (\d{2}):(\d{2}):(\d{2})\] (.+)", line)
        if match:
            start_hr, start_min, start_sec, end_hr, end_min, end_sec, text = match.groups()
            start_time = int(start_hr) * 3600 + int(start_min) * 60 + int(start_sec)
            end_time = int(end_hr) * 3600 + int(end_min) * 60 + int(end_sec)
            timestamp = f"{start_hr}:{start_min}:{start_sec} - {end_hr}:{end_min}:{end_sec}"
        else:
            # Try MM:SS format
            match = re.match(r"\[(\d{2}):(\d{2}) - (\d{2}):(\d{2})\] (.+)", line)
            if not match:
                return line
            start_min, start_sec, end_min, end_sec, text = match.groups()
            start_time = int(start_min) * 60 + int(start_sec)
            end_time = int(end_min) * 60 + int(end_sec)
            timestamp = f"{start_min}:{start_sec} - {end_min}:{end_sec}"

        # Find speaker for this segment (use midpoint for matching)
        midpoint = (start_time + end_time) / 2
        speaker = self._find_speaker_at_time(midpoint, speaker_segments)

        if speaker:
            return f"[{timestamp}] {speaker}: {text}"
        return line

    def _find_speaker_at_time(
        self,
        time: float,
        speaker_segments: list[tuple[float, float, str]],
    ) -> str | None:
        """Find the speaker label at a given time.

        Args:
            time: Time in seconds.
            speaker_segments: List of (start_time, end_time, speaker_label) tuples.

        Returns:
            Speaker label if found, None otherwise.
        """
        for start, end, speaker in speaker_segments:
            if start <= time <= end:
                return speaker
        return None


def format_diarization_output(segments: list[tuple[float, float, str]]) -> str:
    """Format diarization segments into human-readable output.

    Args:
        segments: List of (start_time, end_time, speaker_label) tuples.

    Returns:
        Formatted string with [MM:SS - MM:SS] Speaker format.
    """

    def format_time(seconds: float) -> str:
        total_seconds = int(seconds)
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    lines = []
    for start, end, speaker in segments:
        start_str = format_time(start)
        end_str = format_time(end)
        lines.append(f"[{start_str} - {end_str}] {speaker}")

    return "\n".join(lines)


def get_unique_speakers(segments: list[tuple[float, float, str]]) -> list[str]:
    """Extract unique speaker labels from segments in order of first appearance.

    Args:
        segments: List of (start_time, end_time, speaker_label) tuples.

    Returns:
        List of unique speaker labels in order of first appearance.
    """
    seen = set()
    speakers = []
    for _, _, speaker in segments:
        if speaker not in seen:
            seen.add(speaker)
            speakers.append(speaker)
    return speakers


def get_speaker_context_lines(
    transcript: str,
    speaker_label: str,
    context_lines: int = 5,
) -> list[str]:
    """Extract context lines for a specific speaker's segments from transcript.

    Args:
        transcript: Transcript with [HH:MM:SS - HH:MM:SS] SPEAKER_XX: text format.
                   Also accepts legacy [MM:SS - MM:SS] format for backward compatibility.
        speaker_label: Speaker label to extract contexts for.
        context_lines: Number of lines to show before and after each speaker segment group.

    Returns:
        List of context strings, one per continuous segment group for the speaker.
    """
    # Split transcript into lines
    lines = transcript.split("\n")

    # Build a mapping of line index to speaker label by parsing the line
    line_to_speaker = {}
    for i, line in enumerate(lines):
        # Match pattern: [HH:MM:SS - HH:MM:SS] SPEAKER_XX: text
        # The optional (?:\d{2}:)? group provides backward compatibility with legacy [MM:SS - MM:SS] format
        match = re.match(r"\[(?:\d{2}:)?\d{2}:\d{2} - (?:\d{2}:)?\d{2}:\d{2}\]\s+(SPEAKER_\d+):?", line)
        if match:
            line_to_speaker[i] = match.group(1)

    # Find groups of continuous segments for the speaker
    speaker_groups = []
    current_group = []
    for i in range(len(lines)):
        if line_to_speaker.get(i) == speaker_label:
            current_group.append(i)
        elif current_group:
            # End of a group
            speaker_groups.append(current_group)
            current_group = []
    if current_group:
        speaker_groups.append(current_group)

    # Extract context for each group
    contexts = []
    for group in speaker_groups:
        start_idx = max(0, group[0] - context_lines)
        end_idx = min(len(lines), group[-1] + context_lines + 1)
        context = "\n".join(lines[start_idx:end_idx])
        contexts.append(context)

    return contexts
