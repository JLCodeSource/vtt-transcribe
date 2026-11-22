"""Local Whisper transcription engine (faster-whisper / CTranslate2): no OpenAI key, no network after first run.

Install with ``pip install vtt-transcribe[local]``. Models are downloaded once from the Hugging Face
hub (public ``Systran/faster-whisper-*`` repositories, no token needed) and cached in
``~/.cache/vtt-transcribe/models/whisper`` (override the base directory with ``VTT_MODEL_DIR``).

``LocalTranscriber`` reuses everything in :class:`VideoTranscriber` (audio extraction, path handling,
chunk handling, cleanup) and only replaces the OpenAI API calls, so its output has the same
``[HH:MM:SS - HH:MM:SS] text`` line format and plugs into diarization unchanged.
"""

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vtt_transcribe.logging_config import get_logger
from vtt_transcribe.progress import ProgressCallback, format_clock, report
from vtt_transcribe.transcriber import VideoTranscriber
from vtt_transcribe.transcript_formatter import TranscriptFormatter

logger = get_logger(__name__)

DEFAULT_MODEL = "small"
SAMPLE_RATE = 16000
DETECT_SECONDS = 30
LOCAL_DEPS_ERROR_MSG = "The local engine needs faster-whisper. Install with: pip install vtt-transcribe[local]"


def whisper_model_dir() -> Path:
    """Where Whisper models are cached."""
    override = os.environ.get("VTT_MODEL_DIR")
    if override:
        return Path(override) / "whisper"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "vtt-transcribe" / "models" / "whisper"


def resolve_device(device: str) -> str:
    """Map ``--device`` (auto/cuda/gpu/cpu) to a CTranslate2 device: "cuda" or "cpu"."""
    if device in ("cuda", "gpu"):
        return "cuda"
    if device == "cpu" or os.environ.get("DISABLE_GPU") == "1":
        return "cpu"
    try:
        import ctranslate2  # pyright: ignore[reportMissingImports]

        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def load_audio(path: Path) -> Any:
    """Decode any audio file to 16 kHz mono float32 with ffmpeg (already required by vtt)."""
    import numpy as np

    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
    proc = subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
    if proc.returncode != 0:
        msg = f"ffmpeg failed to decode {path}: {proc.stderr.decode(errors='replace').strip()}"
        raise RuntimeError(msg)
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


class LocalTranscriber(VideoTranscriber):
    """Transcribe with a local faster-whisper model instead of the OpenAI API."""

    # No upload limit locally, so never split into chunks.
    MAX_SIZE_MB = 10**9

    def __init__(
        self,
        model: str | None = None,
        device: str = "auto",
        model_dir: Path | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Remember settings; the model itself loads lazily on first use.

        ``progress_callback(fraction, message)`` is called as segments are produced, with the position in the
        audio divided by its total duration (see ``vtt_transcribe.progress``).
        """
        self.progress_callback = progress_callback
        self.api_key = ""
        self.model_name = model or DEFAULT_MODEL
        self.device = resolve_device(device)
        self._auto = device == "auto"
        self.compute_type = "int8_float16" if self.device == "cuda" else "int8"
        self.model_dir = model_dir or whisper_model_dir()
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel  # pyright: ignore[reportMissingImports]
            except ImportError as e:
                raise ImportError(LOCAL_DEPS_ERROR_MSG) from e
            self.model_dir.mkdir(parents=True, exist_ok=True)
            print(f"Loading Whisper model '{self.model_name}' on {self.device} ({self.compute_type})...", file=sys.stderr)
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(self.model_dir),
            )
        return self._model

    def _with_cpu_fallback(self, work: Callable[[Any], Any]) -> Any:
        """Run ``work(model)``; with ``--device auto`` on a GPU, retry on the CPU if the CUDA libraries are unusable.

        CTranslate2 loads its CUDA libraries (cuBLAS 12, cuDNN 9) lazily, so a missing or mismatched install only
        fails at the first transcription. An explicit ``--device cuda`` still raises.
        """
        try:
            return work(self._get_model())
        except RuntimeError as e:
            if not (self._auto and self.device == "cuda"):
                raise
            logger.warning("CUDA unavailable for the local engine, falling back to the CPU", extra={"error": str(e)})
            print(f"CUDA unavailable ({e}); using the CPU instead.", file=sys.stderr)
            self.device, self.compute_type, self._model = "cpu", "int8", None
            return work(self._get_model())

    def detect_language(self, audio_path: Path) -> str:
        """Detect the spoken language from the first 30 seconds."""
        if not audio_path.exists():
            msg = f"Audio file not found: {audio_path}"
            raise FileNotFoundError(msg)
        audio = load_audio(audio_path)[: DETECT_SECONDS * SAMPLE_RATE]
        language, _probability, _all = self._with_cpu_fallback(lambda m: m.detect_language(audio))
        return str(language)

    def _run(self, audio_path: Path, *, language: str | None, task: str) -> str:
        if not audio_path.exists():
            msg = f"Audio file not found: {audio_path}"
            raise FileNotFoundError(msg)
        start = time.time()
        audio = load_audio(audio_path)

        def work(model: Any) -> tuple[list[Any], Any]:
            segments, info = model.transcribe(audio, language=language, task=task, beam_size=1, vad_filter=True)
            total = float(getattr(info, "duration", 0) or 0)
            report(self.progress_callback, 0.0, "Transcribing")
            out: list[Any] = []
            # consume the lazy generator here so CUDA errors surface inside the fallback
            for seg in segments:
                out.append(seg)
                if total > 0:
                    report(
                        self.progress_callback,
                        float(seg.end) / total,
                        f"Transcribing {format_clock(float(seg.end))} / {format_clock(total)}",
                    )
            return out, info

        segments, info = self._with_cpu_fallback(work)
        report(self.progress_callback, 1.0, "Transcription complete")
        payload = {"segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments]}
        logger.info(
            "Local transcription complete",
            extra={
                "model": self.model_name,
                "device": self.device,
                "language": getattr(info, "language", None),
                "duration_seconds": round(time.time() - start, 2),
            },
        )
        return "\n".join(TranscriptFormatter.format(payload, include_timestamps=True))

    def transcribe_audio_file(self, audio_path: Path, *, language: str | None = None) -> str:
        """Transcribe one audio file; returns timestamped lines like the OpenAI engine."""
        return self._run(audio_path, language=language, task="transcribe")

    def translate_audio_file(self, audio_path: Path) -> str:
        """Translate speech to English (Whisper's translate task), with timestamps."""
        return self._run(audio_path, language=None, task="translate")
