"""Speaker diarization using pyannote.audio (the optional "pyannote" backend).

The backend-independent parts (transcript labelling, formatting helpers) live in
:mod:`vtt_transcribe.diarization_common` and are re-exported here for compatibility.
"""

import os
import re
import warnings
from pathlib import Path

import torch
from pyannote.audio import Pipeline

from vtt_transcribe.diarization_common import (
    PYANNOTE_DEFAULT_SAMPLE_RATE,
    SpeakerLabeler,
    format_diarization_output,
    get_speaker_context_lines,
    get_unique_speakers,
)
from vtt_transcribe.logging_config import get_logger

__all__ = [
    "DEFAULT_DIARIZATION_MODEL",
    "PYANNOTE_DEFAULT_SAMPLE_RATE",
    "SpeakerDiarizer",
    "format_diarization_output",
    "get_speaker_context_lines",
    "get_unique_speakers",
    "resolve_device",
]

logger = get_logger(__name__)


# Constants
DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"


def resolve_device(device: str) -> str:
    """Resolve device string to actual device (cuda or cpu).

    Args:
        device: Device specification ("auto", "cuda", "gpu", or "cpu").

    Returns:
        Resolved device string ("cuda" or "cpu").

    Note:
        If DISABLE_GPU environment variable is set, always returns "cpu".
    """
    # Check if GPU is disabled via env var
    if os.environ.get("DISABLE_GPU"):
        return "cpu"

    # Map "gpu" alias to "cuda"
    if device == "gpu":
        device = "cuda"

    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


class SpeakerDiarizer(SpeakerLabeler):
    """Speaker diarization using pyannote.audio."""

    def __init__(self, hf_token: str | None = None, device: str = "auto") -> None:
        """Initialize diarizer with Hugging Face token.

        Args:
            hf_token: Hugging Face token for model access. If None, uses HF_TOKEN env var.
            device: Device to use ("auto", "cuda", or "cpu"). Default is "auto".

        Raises:
            ValueError: If no token is provided and HF_TOKEN env var is not set.
        """
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        if not self.hf_token:
            msg = "Hugging Face token not provided. Use --hf-token or set HF_TOKEN environment variable."
            raise ValueError(msg)
        self.device = device
        self.pipeline: Pipeline | None = None

    def _load_pipeline(self) -> Pipeline:
        """Lazy load the diarization pipeline and move to device."""
        if self.pipeline is None:
            # Suppress TF32 reproducibility warning from pyannote
            # TF32 is disabled by pyannote for accuracy/reproducibility
            warnings.filterwarnings(
                "ignore",
                category=UserWarning,
                module="pyannote.audio.utils.reproducibility",
                message=".*TF32.*",
            )

            self.pipeline = Pipeline.from_pretrained(
                DEFAULT_DIARIZATION_MODEL,
                token=self.hf_token,
            )
            # Resolve and set device
            resolved_device = resolve_device(self.device)
            device = torch.device(resolved_device)

            logger.info("Loading diarization pipeline on device: %s", resolved_device)

            # Move pipeline to device using its .to() method
            try:
                assert self.pipeline is not None
                self.pipeline.to(device)
                logger.info("Successfully moved diarization pipeline to %s", resolved_device)

                # Verify device placement by checking if GPU memory was allocated
                if resolved_device == "cuda" and torch.cuda.is_available():
                    mem_allocated = torch.cuda.memory_allocated(0) / 1024**2
                    logger.info("GPU memory allocated: %.2f MB", mem_allocated)
                    if mem_allocated < 1.0:
                        logger.warning(
                            "GPU memory allocation is very low (%.2f MB). Pipeline may still be on CPU.",
                            mem_allocated,
                        )
            except Exception as e:
                # Fallback to CPU if device move fails
                logger.warning("Failed to move pipeline to %s: %s. Using CPU.", resolved_device, e)
        assert self.pipeline is not None
        return self.pipeline

    def _diarize_audio_internal(self, audio_path: Path) -> list[tuple[float, float, str]]:
        """Internal diarization implementation."""
        pipeline = self._load_pipeline()

        # Suppress the torch pooling warning about degrees of freedom
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*degrees of freedom.*", category=UserWarning)
            try:
                diarization = pipeline(str(audio_path))
            except ValueError as e:
                error_str = str(e)
                # Check if it's a sample mismatch error from pyannote
                if "requested chunk" in error_str and "samples" in error_str and "instead of the expected" in error_str:
                    # This is a pyannote error - could be file corruption, metadata issues, or truly too short
                    # Extract sample counts to provide better error message
                    match = re.search(r"resulted in (\d+) samples instead of the expected (\d+) samples", error_str)
                    if match:
                        actual_samples = int(match.group(1))
                        expected_samples = int(match.group(2))
                        actual_duration = actual_samples / PYANNOTE_DEFAULT_SAMPLE_RATE
                        expected_duration = expected_samples / PYANNOTE_DEFAULT_SAMPLE_RATE

                        # If actual duration < 9.5 seconds, it's genuinely too short
                        # We allow some tolerance (0.5s) for MP3 encoding imprecision
                        if actual_duration < 9.5:
                            msg = (
                                f"Audio file is too short for diarization ({actual_duration:.2f}s). "
                                f"The pyannote.audio model requires at least 10 seconds of audio."
                            )
                            raise ValueError(msg) from e
                        # File is long enough but has sample mismatch - likely metadata/encoding issue
                        msg = (
                            f"Audio file sample mismatch error. This usually indicates:\n"
                            f"  - MP3 encoding imprecision (metadata doesn't match exact sample count)\n"
                            f"  - File corruption or incomplete download\n"
                            f"  - Unusual encoding that pyannote can't handle properly\n"
                            f"Expected {expected_duration:.2f}s ({expected_samples} samples), "
                            f"but got {actual_duration:.2f}s ({actual_samples} samples).\n\n"
                            f"Try re-encoding to WAV format (more compatible but larger file):\n"
                            f"  ffmpeg -i input.mp3 -acodec pcm_s16le -ar 16000 -ac 1 output.wav"
                        )
                        raise ValueError(msg) from e
                # Other ValueError - just re-raise
                raise

        # pyannote.audio 4.0.7+ types the pipeline output as a union that includes an
        # iterator; the non-streaming call used here always returns DiarizeOutput.
        speaker_diarization = getattr(diarization, "speaker_diarization", None)
        if speaker_diarization is None:
            msg = f"Unexpected diarization output type: {type(diarization).__name__}"
            raise RuntimeError(msg)

        segments = []
        for turn, _, speaker in speaker_diarization.itertracks(yield_label=True):
            segments.append((turn.start, turn.end, speaker))

        return segments
