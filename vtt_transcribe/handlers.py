"""Handler functions for different transcription and diarization workflows."""

import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vtt_transcribe.logging_config import get_logger
from vtt_transcribe.translator import AudioTranslator

logger = get_logger(__name__)

if TYPE_CHECKING:
    from vtt_transcribe.diarization import SpeakerDiarizer, format_diarization_output  # noqa: F401


AUDIO_EXTENSION = ".mp3"
TRANSCRIPT_EXTENSION = ".txt"

# Error message for missing diarization dependencies
DIARIZATION_DEPS_ERROR_MSG = (
    "Diarization dependencies not installed. "
    "Install with: pip install vtt-transcribe[diarization] "
    "or: uv pip install vtt-transcribe[diarization]"
)


def save_transcript(output_path: Path, transcript: str) -> None:
    """Save transcript to a file, ensuring .txt extension and trailing newline."""
    # Ensure output path has .txt extension
    if output_path.suffix.lower() != ".txt":
        output_path = output_path.with_suffix(TRANSCRIPT_EXTENSION)
    if not transcript.endswith("\n"):
        transcript += "\n"

    logger.info(
        "Saving transcript to file",
        extra={
            "output_path": str(output_path),
            "transcript_length": len(transcript),
        },
    )

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
    start_time = time.time()

    logger.info(
        "Starting diarize-only workflow",
        extra={
            "input_path": str(input_path),
            "save_path": str(save_path) if save_path else None,
            "device": device,
        },
    )

    if not input_path.exists():
        msg = f"Audio file not found: {input_path}"
        raise FileNotFoundError(msg)

    SpeakerDiarizer, format_diarization_output, _, _ = _lazy_import_diarization()  # noqa: N806
    print(f"Running speaker diarization on: {input_path}")
    print(f"Using device: {device}")

    # Show GPU info if using CUDA
    gpu_memory_after: float | None = None
    torch_module = None
    if device in ("cuda", "auto"):
        import torch

        torch_module = torch
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"GPU memory before: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

    diarizer = SpeakerDiarizer(hf_token=hf_token, device=device)
    segments = diarizer.diarize_audio(input_path)

    # Show GPU memory after if using CUDA
    if device in ("cuda", "auto") and torch_module is not None and torch_module.cuda.is_available():
        gpu_memory_after = torch_module.cuda.memory_allocated(0) / 1024**2
        print(f"GPU memory after: {gpu_memory_after:.2f} MB")

    result = format_diarization_output(segments)
    display_result(result)

    if save_path:
        save_transcript(save_path, result)

    duration = time.time() - start_time
    logger.info(
        "Diarize-only workflow complete",
        extra={
            "duration_seconds": round(duration, 2),
            "num_segments": len(segments),
            "result_length": len(result),
        },
    )

    return result


def handle_apply_diarization_mode(
    input_path: Path, transcript_path: Path, hf_token: str | None, save_path: Path | None, device: str = "auto"
) -> str:
    """Handle --apply-diarization mode: apply diarization to existing transcript.

    Returns:
        The transcript with speaker labels applied.
    """
    start_time = time.time()

    logger.info(
        "Starting apply-diarization workflow",
        extra={
            "input_path": str(input_path),
            "transcript_path": str(transcript_path),
            "save_path": str(save_path) if save_path else None,
            "device": device,
        },
    )

    if not transcript_path.exists():
        msg = f"Transcript file not found: {transcript_path}"
        raise FileNotFoundError(msg)

    if not input_path.exists():
        msg = f"Audio file not found: {input_path}"
        raise FileNotFoundError(msg)

    # Load transcript
    logger.info("Loading transcript file", extra={"path": str(transcript_path)})
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

    duration = time.time() - start_time
    logger.info(
        "Apply-diarization workflow complete",
        extra={
            "duration_seconds": round(duration, 2),
            "num_segments": len(segments),
            "result_length": len(result),
        },
    )

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
        # Match pattern: [HH:MM:SS - HH:MM:SS] or [MM:SS - MM:SS] SPEAKER_XX: text (with colon)
        # or [HH:MM:SS - HH:MM:SS] / [MM:SS - MM:SS] SPEAKER_XX (without colon, from diarization-only output)
        match = re.match(r"\[(?:\d{2}:)?\d{2}:\d{2} - (?:\d{2}:)?\d{2}:\d{2}\]\s+(SPEAKER_\d+):?", line)
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
    start_time = time.time()

    logger.info(
        "Starting speaker review workflow",
        extra={
            "input_path": str(input_path) if input_path else None,
            "has_transcript": transcript is not None,
            "save_path": str(save_path) if save_path else None,
        },
    )

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

    duration = time.time() - start_time
    logger.info(
        "Speaker review workflow complete",
        extra={
            "duration_seconds": round(duration, 2),
            "speakers_reviewed": len(speakers),
        },
    )

    return final_transcript


def _lazy_import_diarization() -> tuple:
    """Lazy import diarization module to avoid loading torch on --help."""
    try:
        from vtt_transcribe.diarization import (
            SpeakerDiarizer,
            format_diarization_output,
            get_speaker_context_lines,
            get_unique_speakers,
        )
    except (ImportError, ModuleNotFoundError) as e:
        # Handle missing module scenarios for both package installation and direct execution
        is_missing_package_module = isinstance(e, ModuleNotFoundError) and e.name in (
            "vtt_transcribe.diarization",
            "vtt_transcribe",
        )
        is_missing_dependency = isinstance(e, ModuleNotFoundError) and not is_missing_package_module

        # Plain ImportError (without a .name attribute) could be:
        # 1. Direct execution fallback scenario (module not found as package)
        # 2. Real implementation bugs (e.g., "cannot import name X")
        # We try the fallback path first for (1), and if that fails, we know it's (2)
        is_plain_import_error = isinstance(e, ImportError) and not isinstance(e, ModuleNotFoundError)

        if is_missing_package_module or is_plain_import_error:
            # Fallback for direct execution when package module doesn't exist
            # Save reference to original exception for potential re-raise
            original_exception = e
            try:
                from diarization import (  # type: ignore[no-redef]
                    SpeakerDiarizer,
                    format_diarization_output,
                    get_speaker_context_lines,
                    get_unique_speakers,
                )
            except ImportError as e2:
                # If fallback also fails, check if original was missing deps
                # or if this is a real bug that should be re-raised
                if is_plain_import_error:
                    # Original was plain ImportError - this is likely a real bug
                    # Explicitly raise the original exception to preserve its traceback
                    # and chain the fallback failure as the cause
                    raise original_exception from e2
                # Original was missing package module, fallback failed too
                raise ImportError(DIARIZATION_DEPS_ERROR_MSG) from e2
        elif is_missing_dependency:
            # Missing dependency within the diarization module (e.g., torch, pyannote.audio)
            raise ImportError(DIARIZATION_DEPS_ERROR_MSG) from e
        else:  # pragma: no cover
            # Should never reach here, but re-raise just in case
            raise
    return SpeakerDiarizer, format_diarization_output, get_unique_speakers, get_speaker_context_lines


def _detect_or_override_language(args: Any, transcriber: Any, input_path: Path) -> tuple[str | None, str | None]:
    """Detect language or use manual override.

    Returns:
        Tuple of (detected_language, language_to_use)
        - detected_language: The detected language code (or None if manually specified)
        - language_to_use: The language to pass to transcription (or None to let Whisper detect)
    """
    if hasattr(args, "language") and args.language:
        # Manual override
        print(f"Using manually specified language: {args.language}", file=sys.stderr)
        return None, args.language

    # Auto-detect language before transcription
    # First, ensure we have an audio file
    is_audio_input = input_path.suffix.lower() in transcriber.SUPPORTED_AUDIO_FORMATS
    if is_audio_input:
        audio_for_detection = input_path
    else:
        # Need to extract audio first
        audio_for_detection = (
            Path(args.output_audio) if args.output_audio else transcriber.resolve_audio_path(input_path, None)
        )
        if not audio_for_detection.exists() or args.force:
            transcriber.extract_audio(input_path, audio_for_detection, force=args.force)

    print("Detecting language...", file=sys.stderr)
    detected_language = transcriber.detect_language(audio_for_detection)
    print(f"Detected language: {detected_language}", file=sys.stderr)
    return detected_language, None  # Let Whisper detect it during transcription too


def handle_standard_transcription(args: Any, api_key: str) -> str:
    """Handle standard transcription workflow with optional diarization and translation.

    Returns:
        The final transcript (with or without speaker labels and/or translation).
    """
    start_time = time.time()

    logger.info(
        "Starting standard transcription workflow",
        extra={
            "input_file": args.input_file,
            "translate": args.translate if hasattr(args, "translate") else False,
            "diarize": args.diarize if hasattr(args, "diarize") else False,
            "translate_to": args.translate_to if hasattr(args, "translate_to") else None,
            "language": args.language if hasattr(args, "language") else None,
        },
    )

    from vtt_transcribe.transcriber import VideoTranscriber

    # Handle --translate flag (audio translation)
    if args.translate:
        translator = AudioTranslator(api_key)
        input_path = Path(args.input_file)

        # For audio translation, we need the audio file
        if input_path.suffix.lower() not in VideoTranscriber.SUPPORTED_AUDIO_FORMATS:
            # Extract audio first
            transcriber = VideoTranscriber(api_key)
            audio_path = Path(args.output_audio) if args.output_audio else None
            audio_path = transcriber.resolve_audio_path(input_path, audio_path)
            keep_audio = not args.delete_audio
            transcriber.extract_audio(input_path, audio_path, force=args.force)
            actual_audio_path = audio_path
        else:
            actual_audio_path = input_path
            keep_audio = True

        print("Translating audio to English...")
        result = translator.translate_audio_file(actual_audio_path)

        # Cleanup audio if requested
        if not keep_audio and actual_audio_path != input_path:
            actual_audio_path.unlink()
            print(f"Deleted audio file: {actual_audio_path}")

        return result

    transcriber = VideoTranscriber(api_key)

    input_path = Path(args.input_file)
    audio_path = Path(args.output_audio) if args.output_audio else None
    keep_audio = not args.delete_audio

    # Detect or use manual language override
    _detected_language, language_to_use = _detect_or_override_language(args, transcriber, input_path)

    result = transcriber.transcribe(
        input_path,
        audio_path,
        force=args.force,
        keep_audio=keep_audio,
        scan_chunks=args.scan_chunks,
        language=language_to_use,
    )

    # Apply diarization if requested
    if args.diarize:
        SpeakerDiarizer, _, _, _ = _lazy_import_diarization()  # noqa: N806
        diarizer = SpeakerDiarizer(hf_token=args.hf_token, device=args.device)
        # Determine the audio path used for transcription
        # After transcribe() has run, the audio file should exist at the expected location
        if input_path.suffix.lower() in VideoTranscriber.SUPPORTED_AUDIO_FORMATS:
            # Input was audio, it was used directly
            actual_audio_path = input_path
        elif audio_path:
            # Custom audio output path was specified
            actual_audio_path = audio_path
        else:
            # Default audio path (video name with .mp3 extension)
            actual_audio_path = input_path.with_suffix(AUDIO_EXTENSION)

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

    # Apply text translation if requested
    if args.translate_to:
        translator = AudioTranslator(api_key)
        print(f"\nTranslating transcript to {args.translate_to}...")
        result = translator.translate_text(result, target_language=args.translate_to)

    duration = time.time() - start_time
    logger.info(
        "Standard transcription workflow complete",
        extra={
            "duration_seconds": round(duration, 2),
            "result_length": len(result),
        },
    )

    return result
