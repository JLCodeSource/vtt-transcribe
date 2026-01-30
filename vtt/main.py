import argparse
import contextlib
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openai import OpenAI

from vtt.audio_chunker import AudioChunker
from vtt.audio_manager import AudioFileManager
from vtt.transcript_formatter import TranscriptFormatter

if TYPE_CHECKING:
    from openai.types.audio.transcription_verbose import TranscriptionVerbose

    from vtt.diarization import SpeakerDiarizer, format_diarization_output  # noqa: F401

# Constants
MAX_FILE_SIZE_MB = 25
AUDIO_EXTENSION = ".mp3"
VIDEO_EXTENSION = ".mp4"
TRANSCRIPT_EXTENSION = ".txt"
CHUNK_SAFETY_FACTOR = 0.9
SECONDS_PER_MINUTE = 60


class VideoTranscriber:
    """Transcribe video audio using OpenAI's Whisper model."""

    MAX_SIZE_MB = MAX_FILE_SIZE_MB
    SUPPORTED_AUDIO_FORMATS = (".mp3", ".wav", ".ogg", ".m4a")

    def __init__(self, api_key: str) -> None:
        """Initialize transcriber with API key."""
        self.api_key: str = api_key
        self.client = OpenAI(api_key=api_key)

    def validate_input_file(self, input_path: Path) -> Path:
        """Validate and return video file path."""
        if not input_path.exists():
            msg = f"Input file not found: {input_path}"
            raise FileNotFoundError(msg)
        return input_path

    def resolve_audio_path(self, input_path: Path, audio_path: Path | None) -> Path:
        """Resolve audio file path, ensuring .mp3 extension."""
        if audio_path is None:
            return input_path.with_suffix(AUDIO_EXTENSION)
        # Custom audio path handling
        if audio_path.suffix.lower() == ".mp3":
            # Already has .mp3 extension, accept as-is
            return audio_path
        if audio_path.suffix == "":
            # No extension, add .mp3
            return audio_path.with_suffix(AUDIO_EXTENSION)
        # Different extension, raise error
        msg = f"Audio file must have .mp3 extension, got: {audio_path}"
        raise ValueError(msg)

    def extract_audio(self, input_path: Path, audio_path: Path, *, force: bool = False) -> None:
        """Extract audio from video file (delegates to AudioFileManager)."""
        if audio_path.exists() and not force:
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            print(f"Using existing audio file: {audio_path} ({file_size_mb:.1f}MB)")
            return
        AudioFileManager.extract_from_video(input_path, audio_path, force=force)

    def get_audio_duration(self, audio_path: Path) -> float:
        """Get audio file duration (delegates to AudioFileManager)."""
        return AudioFileManager.get_duration(audio_path)

    def find_existing_chunks(self, audio_path: Path) -> list[Path]:
        """Find all chunk files (delegates to AudioFileManager)."""
        return AudioFileManager.find_chunks(audio_path)

    def cleanup_audio_files(self, audio_path: Path) -> None:
        """Delete audio file and chunks (delegates to AudioFileManager)."""
        # Find chunks before deleting
        chunks = AudioFileManager.find_chunks(audio_path)

        # Delete everything
        AudioFileManager.cleanup_files(audio_path)

        # Report what was deleted
        print(f"Deleted audio file: {audio_path}")
        for chunk in chunks:
            print(f"Deleted chunk file: {chunk}")

    def cleanup_audio_chunks(self, audio_path: Path) -> None:
        """Delete only chunk files (delegates to AudioFileManager)."""
        chunks = AudioFileManager.find_chunks(audio_path)
        AudioFileManager.cleanup_chunks_only(audio_path)
        if chunks:
            print(f"Deleted {len(chunks)} chunk files")

    def calculate_chunk_params(self, file_size_mb: float, duration: float) -> tuple[int, float]:
        """Calculate chunk parameters (delegates to AudioChunker)."""
        return AudioChunker.calculate_chunk_params(file_size_mb, duration)

    def extract_audio_chunk(self, audio_path: Path, start_time: float, end_time: float, chunk_index: int) -> Path:
        """Extract audio chunk (delegates to AudioFileManager)."""
        return AudioFileManager.extract_chunk(audio_path, start_time, end_time, chunk_index)

    def transcribe_audio_file(self, audio_path: Path) -> str:
        """Transcribe a single audio file using Whisper API with timestamps."""
        with open(audio_path, "rb") as audio_file:
            response: TranscriptionVerbose = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
            )

        formatted = self._format_transcript_with_timestamps(response)

        # Diagnostic: if we got an empty transcript, print response details
        if not formatted or not formatted.strip():
            try:
                print("DEBUG: Empty formatted transcript produced")
                print(f"DEBUG: response type: {type(response)!r}")
                # If it's a dict-like response, show top-level keys
                if isinstance(response, dict):
                    print(f"DEBUG: response keys: {list(response.keys())}")
                    # If there is raw text, print a preview
                    if "text" in response:
                        preview = (response.get("text") or "")[:200]
                        print(f"DEBUG: response[text] preview: {preview!r}")
                else:
                    preview = str(response)[:400]
                    print(f"DEBUG: response preview: {preview!r}")
            except Exception as e:
                msg = f"DEBUG: error while printing response: {e}"
                print(msg)

        return formatted

    def _format_transcript_with_timestamps(self, response: "TranscriptionVerbose") -> str:
        """Format transcript with timestamps (delegates to TranscriptFormatter)."""
        lines = TranscriptFormatter.format(response, include_timestamps=True)
        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp (delegates to TranscriptFormatter)."""
        return TranscriptFormatter._format_timestamp(seconds)  # noqa: SLF001

    def transcribe_chunked_audio(
        self,
        audio_path: Path,
        duration: float,
        num_chunks: int,
        chunk_duration: float,
        *,
        keep_chunks: bool = False,
    ) -> str:
        """Transcribe audio by splitting into chunks.

        This method will reuse existing chunk files when they already exist and
        match the expected number of chunks. The actual transcription and
        per-chunk cleanup logic is delegated to `_transcribe_chunk_files` to
        reduce cyclomatic complexity.
        """
        print(f"Splitting into {num_chunks} chunks ({chunk_duration:.1f}s each)...")

        # Determine chunk file list: reuse existing or create new ones
        existing_chunks = self.find_existing_chunks(audio_path)
        if existing_chunks and len(existing_chunks) == num_chunks:
            chunk_files = existing_chunks
        else:
            chunk_files = []
            for i in range(num_chunks):
                start_time: float = i * chunk_duration
                end_time: float = min((i + 1) * chunk_duration, duration)

                # Extract chunk file
                chunk_path: Path = self.extract_audio_chunk(audio_path, start_time, end_time, i)
                chunk_files.append(chunk_path)

        transcripts = self._transcribe_chunk_files(chunk_files, chunk_duration, keep_chunks=keep_chunks)

        if keep_chunks and chunk_files:
            print(f"Kept {len(chunk_files)} chunk files for reference")

        return " ".join(transcripts)

    def _transcribe_chunk_files(self, chunk_files: list[Path], chunk_duration: float, *, keep_chunks: bool) -> list[str]:
        """Transcribe provided chunk files and optionally remove them.

        Using `contextlib.suppress` to ignore unlink errors and keeping this
        logic isolated reduces complexity in the main method.
        """
        transcripts: list[str] = []
        for i, chunk_path in enumerate(chunk_files):
            start_time = i * chunk_duration
            print(f"Transcribing chunk {i + 1}/{len(chunk_files)}...")
            transcript: str = self.transcribe_audio_file(chunk_path)
            if transcript and start_time > 0:
                transcript = self._shift_formatted_timestamps(transcript, start_time)
            transcripts.append(transcript)
            if not keep_chunks:
                with contextlib.suppress(Exception):
                    chunk_path.unlink()

        return transcripts

    def _shift_formatted_timestamps(self, formatted: str, offset_seconds: float) -> str:
        """Shift timestamps in formatted transcript (delegates to TranscriptFormatter)."""
        lines = formatted.split("\n")
        adjusted_lines = TranscriptFormatter.adjust_timestamps(lines, offset_seconds)
        return "\n".join(adjusted_lines)

    def _transcribe_sibling_chunks(self, base_audio_path: Path) -> str:
        """Transcribe all sibling chunks with timestamp shifting."""
        all_chunks = self.find_existing_chunks(base_audio_path)
        if not all_chunks:
            return ""

        print(f"Found {len(all_chunks)} chunk files, processing in order...")
        transcripts = []
        cumulative_start = 0.0
        for chunk_path in all_chunks:
            print(f"Transcribing {chunk_path.name}...")
            transcript = self.transcribe_audio_file(chunk_path)
            # Shift timestamps by cumulative offset for chunks after the first
            if transcript and cumulative_start > 0:
                transcript = self._shift_formatted_timestamps(transcript, cumulative_start)
            transcripts.append(transcript)
            # Update cumulative start by the duration of this chunk
            with contextlib.suppress(Exception):
                cumulative_start += self.get_audio_duration(chunk_path)
        # Separate chunk transcripts with blank lines for readability
        return "\n\n".join(transcripts)

    def transcribe(
        self,
        input_path: Path,
        audio_path: Path | None = None,
        *,
        force: bool = False,
        keep_audio: bool = True,
        scan_chunks: bool = False,
    ) -> str:
        """
        Transcribe video audio using OpenAI's Whisper model.

        Args:
            input_path: Path to the video file or audio file
            audio_path: Optional path for extracted audio file. If not provided, creates one based on video name
            force: If True, re-extract audio even if it exists
            keep_audio: If True, keep audio files after transcription. If False, delete them.
            scan_chunks: If True and input is a chunk file, find and process all sibling chunks in order

        Returns:
            Transcribed text from the video audio
        """
        # Check if input is already an audio file
        is_audio_input = input_path.suffix.lower() in self.SUPPORTED_AUDIO_FORMATS

        if is_audio_input:
            # Validate audio file exists
            if not input_path.exists():
                msg = f"Audio file not found: {input_path}"
                raise FileNotFoundError(msg)

            # Reject -o flag with audio input
            if audio_path is not None:
                msg = "Cannot specify -o/--output-audio when input is already an audio file"
                raise ValueError(msg)

            # Direct audio input: use it directly, no extraction needed
            audio_path = input_path

            # Check if this is a chunk file and scan_chunks is enabled
            if scan_chunks and "_chunk" in audio_path.stem:
                # Extract base name (remove _chunkN suffix)
                base_stem = audio_path.stem.split("_chunk")[0]
                base_audio_path = audio_path.with_stem(base_stem)
                # Find and transcribe all sibling chunks
                result = self._transcribe_sibling_chunks(base_audio_path)
                if result:
                    return result
        else:
            # Validate inputs
            input_path = self.validate_input_file(input_path)
            audio_path = self.resolve_audio_path(input_path, audio_path)

            # Extract audio
            self.extract_audio(input_path, audio_path, force=force)

        # Get file size
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)

        # Transcribe
        if file_size_mb > self.MAX_SIZE_MB:
            print(f"Audio file is {file_size_mb:.1f}MB (limit: {self.MAX_SIZE_MB}MB). Chunking...")
            duration = self.get_audio_duration(audio_path)
            num_chunks, chunk_duration = self.calculate_chunk_params(file_size_mb, duration)
            result = self.transcribe_chunked_audio(
                audio_path,
                duration,
                num_chunks,
                chunk_duration,
                keep_chunks=keep_audio,
            )
        else:
            print("Transcribing audio...")
            result = self.transcribe_audio_file(audio_path)

        # Clean up audio files if not keeping them
        if not keep_audio:
            self.cleanup_audio_files(audio_path)

        return result


def get_api_key(api_key_arg: str | None) -> str:
    """Get API key from argument or environment variable."""
    api_key = api_key_arg or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OpenAI API key not provided. Use -k/--api-key or set OPENAI_API_KEY environment variable."
        raise ValueError(msg)
    return api_key


def save_transcript(output_path: Path, transcript: str) -> None:
    """Save transcript to a file, ensuring .txt extension."""
    # Ensure output path has .txt extension
    if output_path.suffix.lower() != ".txt":
        output_path = output_path.with_suffix(TRANSCRIPT_EXTENSION)
    output_path.write_text(transcript)
    print(f"\nTranscript saved to: {output_path}")


def display_result(transcript: str) -> None:
    """Display transcription result."""
    print("\n" + "=" * 50)
    print("Transcription Result:")
    print("=" * 50)
    print(transcript)


def handle_diarize_only_mode(input_path: Path, hf_token: str | None, save_path: Path | None, device: str = "auto") -> str:
    """Handle --diarize-only mode: run diarization without transcription.

    Returns:
        The formatted diarization output transcript.
    """
    if not input_path.exists():
        msg = f"Audio file not found: {input_path}"
        raise FileNotFoundError(msg)

    SpeakerDiarizer, format_diarization_output, _, _ = _lazy_import_diarization()  # noqa: N806
    print(f"Running speaker diarization on: {input_path}")
    print(f"Using device: {device}")

    # Show GPU info if using CUDA
    if device in ("cuda", "auto"):
        import torch

        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"GPU memory before: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

    diarizer = SpeakerDiarizer(hf_token=hf_token, device=device)
    segments = diarizer.diarize_audio(input_path)

    # Show GPU memory after if using CUDA
    if device in ("cuda", "auto") and torch.cuda.is_available():
        print(f"GPU memory after: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

    result = format_diarization_output(segments)
    display_result(result)

    if save_path:
        save_transcript(save_path, result)

    return result


def handle_apply_diarization_mode(
    input_path: Path, transcript_path: Path, hf_token: str | None, save_path: Path | None, device: str = "auto"
) -> str:
    """Handle --apply-diarization mode: apply diarization to existing transcript.

    Returns:
        The transcript with speaker labels applied.
    """
    if not transcript_path.exists():
        msg = f"Transcript file not found: {transcript_path}"
        raise FileNotFoundError(msg)

    if not input_path.exists():
        msg = f"Audio file not found: {input_path}"
        raise FileNotFoundError(msg)

    # Load transcript
    transcript = transcript_path.read_text()

    # Run diarization
    SpeakerDiarizer, _, _, _ = _lazy_import_diarization()  # noqa: N806
    diarizer = SpeakerDiarizer(hf_token=hf_token, device=device)
    print(f"Running speaker diarization on: {input_path}")
    segments = diarizer.diarize_audio(input_path)

    # Apply speakers to transcript
    print("Applying speaker labels to transcript...")
    result = diarizer.apply_speakers_to_transcript(transcript, segments)
    display_result(result)

    if save_path:
        save_transcript(save_path, result)

    return result


def _load_transcript_from_input(input_path: Path, hf_token: str | None, device: str) -> str:
    """Load or generate transcript from input path."""
    is_transcript = input_path.suffix.lower() in [".txt", ".srt", ".vtt"]

    if is_transcript:
        print(f"Loading transcript from: {input_path}")
        return input_path.read_text()

    # Run diarization on audio file
    SpeakerDiarizer, format_diarization_output, _, _ = _lazy_import_diarization()  # noqa: N806
    diarizer = SpeakerDiarizer(hf_token=hf_token, device=device)
    print(f"Running speaker diarization on: {input_path}")
    segments = diarizer.diarize_audio(input_path)
    return format_diarization_output(segments)


def _extract_speakers_from_transcript(transcript: str) -> list[str]:
    """Extract unique speaker labels from transcript in order of appearance."""
    speakers = []
    seen = set()
    for line in transcript.split("\n"):
        # Match pattern: [HH:MM:SS - HH:MM:SS] SPEAKER_XX: text (with colon)
        # or [HH:MM:SS - HH:MM:SS] SPEAKER_XX (without colon, from diarization-only output)
        match = re.match(r"\[\d{2}:\d{2}:\d{2} - \d{2}:\d{2}:\d{2}\]\s+(SPEAKER_\d+):?", line)
        if match:
            speaker = match.group(1)
            if speaker not in seen:
                seen.add(speaker)
                speakers.append(speaker)
    return speakers


def _review_speaker_interactively(speaker: str, transcript: str, get_speaker_context_lines: Any) -> tuple[str, str | None]:
    """Review a single speaker and prompt for renaming.

    Returns:
        Tuple of (updated_transcript, new_name_or_none)
    """
    contexts = get_speaker_context_lines(transcript, speaker, context_lines=5)

    print(f"\n{'=' * 50}")
    print(f"Speaker: {speaker}")
    print(f"{'=' * 50}")
    speaker_count = transcript.count(speaker)
    print(f"Number of occurrences: {speaker_count}")
    print("\nContext (showing first occurrence):")
    if contexts:
        print(contexts[0])

    new_name = input(f"\nEnter name for {speaker} (or press Enter to keep): ").strip()
    if new_name:
        transcript = transcript.replace(speaker, new_name)
        print(f"Renamed {speaker} -> {new_name}")
        return transcript, new_name

    return transcript, None


def handle_review_speakers(
    input_path: Path | None = None,
    hf_token: str | None = None,
    save_path: Path | None = None,
    device: str = "auto",
    transcript: str | None = None,
) -> str:
    """Handle interactive speaker review and renaming for diarization workflows.

    This function implements the review step that runs automatically in
    diarization modes, unless disabled with ``--no-review-speakers``. It is
    used internally and is not exposed as a direct CLI flag.

    Args:
        input_path: Path to audio/transcript file (required if transcript is None).
        hf_token: Hugging Face token for pyannote models (required if running diarization).
        save_path: Optional path to save final transcript.
        device: Device to use for diarization (auto/cuda/cpu).
        transcript: Pre-computed transcript string. If provided, skips diarization step.

    Returns:
        Final transcript with speaker labels applied.
    """
    _, _, _get_unique_speakers, get_speaker_context_lines = _lazy_import_diarization()

    # Determine final transcript source
    if transcript is not None:
        final_transcript = transcript
    elif input_path is None:
        msg = "Either input_path or transcript must be provided"
        raise ValueError(msg)
    elif not input_path.exists():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)
    else:
        final_transcript = _load_transcript_from_input(input_path, hf_token, device)

    # Extract and review speakers
    speakers = _extract_speakers_from_transcript(final_transcript)
    print(f"\nFound {len(speakers)} speakers: {', '.join(speakers)}")
    print("\nReviewing speakers...")

    for speaker in speakers:
        final_transcript, _ = _review_speaker_interactively(speaker, final_transcript, get_speaker_context_lines)

    display_result(final_transcript)

    if save_path:
        save_transcript(save_path, final_transcript)

    return final_transcript


def _lazy_import_diarization() -> tuple:
    """Lazy import diarization module to avoid loading torch on --help."""
    try:
        from vtt.diarization import (
            SpeakerDiarizer,
            format_diarization_output,
            get_speaker_context_lines,
            get_unique_speakers,
        )
    except ImportError:
        # Fallback for direct execution
        from diarization import (  # type: ignore[no-redef]
            SpeakerDiarizer,
            format_diarization_output,
            get_speaker_context_lines,
            get_unique_speakers,
        )
    return SpeakerDiarizer, format_diarization_output, get_unique_speakers, get_speaker_context_lines


def _handle_standard_transcription(args: Any, api_key: str) -> str:
    """Handle standard transcription workflow with optional diarization.

    Returns:
        The final transcript (with or without speaker labels).
    """
    transcriber = VideoTranscriber(api_key)

    input_path = Path(args.input_file)
    audio_path = Path(args.output_audio) if args.output_audio else None
    keep_audio = not args.delete_audio
    result = transcriber.transcribe(
        input_path, audio_path, force=args.force, keep_audio=keep_audio, scan_chunks=args.scan_chunks
    )

    # Apply diarization if requested
    if args.diarize:
        SpeakerDiarizer, _, _, _ = _lazy_import_diarization()  # noqa: N806
        diarizer = SpeakerDiarizer(hf_token=args.hf_token, device=args.device)
        # Determine the audio path used for transcription
        actual_audio_path = audio_path if audio_path else input_path.with_suffix(AUDIO_EXTENSION)
        if input_path.suffix.lower() in VideoTranscriber.SUPPORTED_AUDIO_FORMATS:
            actual_audio_path = input_path

        print("\nRunning speaker diarization...")
        segments = diarizer.diarize_audio(actual_audio_path)
        result = diarizer.apply_speakers_to_transcript(result, segments)

        # Run speaker review unless disabled
        if not args.no_review_speakers:
            result = handle_review_speakers(
                input_path=None,
                hf_token=args.hf_token,
                save_path=None,  # Don't auto-save during review, we'll save at end
                device=args.device,
                transcript=result,
            )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe video or audio files using OpenAI's Whisper model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4                           # Basic transcription
  %(prog)s audio.mp3 --diarize                 # Audio with speaker identification
  %(prog)s video.mp4 --diarize -s output.txt   # Save diarized transcript
  %(prog)s audio.mp3 --diarize-only            # Only identify speakers
  %(prog)s --apply-diarization transcript.txt audio.mp3  # Add speakers to existing transcript

Environment Variables:
  OPENAI_API_KEY    OpenAI API key for transcription
  HF_TOKEN          Hugging Face token for diarization (requires model access)
  DISABLE_GPU       Set to 1 to force CPU usage for diarization
        """,
    )

    # Positional arguments
    parser.add_argument(
        "input_file",
        help="Path to the video or audio file to transcribe (.mp4, .mp3, .wav, .ogg, .m4a)",
    )

    # API credentials
    api_group = parser.add_argument_group("API Credentials")
    api_group.add_argument(
        "-k",
        "--api-key",
        help="OpenAI API key (defaults to OPENAI_API_KEY environment variable)",
    )
    api_group.add_argument(
        "--hf-token",
        help="Hugging Face token for pyannote.audio models (defaults to HF_TOKEN environment variable)",
    )

    # Input/Output options
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument(
        "-o",
        "--output-audio",
        help="Path for extracted audio file (defaults to input name with .mp3 extension)",
    )
    io_group.add_argument(
        "-s",
        "--save-transcript",
        help="Path to save the transcript to a file",
    )

    # Processing options
    process_group = parser.add_argument_group("Processing Options")
    process_group.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Re-extract audio even if it already exists",
    )
    process_group.add_argument(
        "--delete-audio",
        action="store_true",
        help="Delete audio files after transcription (default: keep audio files)",
    )
    process_group.add_argument(
        "--scan-chunks",
        action="store_true",
        help="When input is a chunk file, detect and process all sibling chunks in order",
    )

    # Diarization options
    diarize_group = parser.add_argument_group("Speaker Diarization Options")
    diarize_group.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization using pyannote.audio",
    )
    diarize_group.add_argument(
        "--device",
        choices=["auto", "cuda", "gpu", "cpu"],
        default="auto",
        help=(
            "Device for diarization: 'auto' (GPU if available), 'gpu'/'cuda' (force GPU), 'cpu'."
            " Set DISABLE_GPU=1 to force CPU."
        ),
    )
    diarize_group.add_argument(
        "--diarize-only",
        action="store_true",
        help="Run diarization on existing audio file without transcription",
    )
    diarize_group.add_argument(
        "--apply-diarization",
        help="Apply diarization to an existing transcript file",
    )
    diarize_group.add_argument(
        "--no-review-speakers",
        action="store_true",
        help="Skip interactive speaker review (default: review is ON for all diarization modes)",
    )

    args = parser.parse_args()

    try:
        # When running only diarization or applying diarization, OpenAI API key is not required
        api_key = None if args.diarize_only or args.apply_diarization else get_api_key(args.api_key)

        # Handle diarization-only mode
        if args.diarize_only:
            save_path = Path(args.save_transcript) if args.save_transcript else None
            diarization_result = handle_diarize_only_mode(Path(args.input_file), args.hf_token, save_path, args.device)

            # Run review unless disabled
            if not args.no_review_speakers:
                # Pass the diarization result directly to avoid redundant diarization
                handle_review_speakers(
                    input_path=None,
                    hf_token=args.hf_token,
                    save_path=save_path,
                    device=args.device,
                    transcript=diarization_result,
                )
            return

        # Handle apply-diarization mode
        if args.apply_diarization:
            save_path = Path(args.save_transcript) if args.save_transcript else None
            apply_result = handle_apply_diarization_mode(
                Path(args.input_file), Path(args.apply_diarization), args.hf_token, save_path, args.device
            )

            # Run review unless disabled
            if not args.no_review_speakers:
                # Pass the result directly to avoid redundant file I/O
                handle_review_speakers(
                    input_path=None,
                    hf_token=args.hf_token,
                    save_path=save_path,
                    device=args.device,
                    transcript=apply_result,
                )
            return

        # Standard transcription flow
        # api_key was already obtained at line 691, no need to call get_api_key again
        assert api_key is not None  # Should be set by line 691 for this path
        result = _handle_standard_transcription(args, api_key)
        display_result(result)

        if args.save_transcript:
            save_transcript(Path(args.save_transcript), result)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
