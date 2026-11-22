"""Speaker diarization with sherpa-onnx (the default "sherpa" backend).

Runs two small ONNX models on the CPU, with no torch, no Hugging Face token and no gated model
terms:

* pyannote-segmentation-3.0 (ONNX export, MIT licence) finds who speaks when.
* NVIDIA NeMo TitaNet-small (CC-BY-4.0) gives each stretch a voice fingerprint that is clustered
  into speakers.

Models (about 46 MB) are downloaded once from the sherpa-onnx GitHub releases, checked against
pinned SHA-256 hashes, and cached in ``~/.cache/vtt-transcribe/models`` (override with
``VTT_MODEL_DIR``).
"""

import hashlib
import os
import tarfile
import tempfile
import urllib.request
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vtt_transcribe.diarization_common import SpeakerLabeler
from vtt_transcribe.logging_config import get_logger
from vtt_transcribe.progress import ProgressCallback

logger = get_logger(__name__)

_RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
# Chosen by sweeping 0.8-1.05 on eight 3-minute LibriSpeech conversations (2-6 speakers):
# lowest mean diarization error rate (12.7%) at 0.95, 12.8% at 1.0.
DEFAULT_THRESHOLD = 0.95
# Second pass: 0.95 merges similar voices (two people in the 4-turn hello_conversation sample came out as one),
# while 0.90 over-splits some multi-speaker files (mean DER 14.3% vs 12.7%). So 0.95 stays the first pass, and only
# when it finds a single speaker is the audio re-clustered at 0.90; that result is kept only if the split looks
# real: the smaller speaker has at least RECLUSTER_MIN_SHARE of the speech time and the audio has at least
# RECLUSTER_MIN_TURNS turns in total.
RECLUSTER_THRESHOLD = 0.90
RECLUSTER_MIN_SHARE = 0.15
RECLUSTER_MIN_TURNS = 3
SAMPLE_RATE = 16000


@dataclass(frozen=True)
class ModelFile:
    """A model artifact: where to get it, how to verify it, and what to keep."""

    url: str
    sha256: str
    #: sha256 of the final .onnx file (the same as ``sha256`` unless it is extracted from an archive)
    target_sha256: str
    #: path of the usable .onnx file relative to the model directory
    target: str
    #: if set, the download is a .tar.bz2 and this member is extracted to ``target``
    archive_member: str | None = None


SEGMENTATION_MODEL = ModelFile(
    url=f"{_RELEASES}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
    sha256="24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488",
    target_sha256="220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079",
    target="pyannote-segmentation-3-0.onnx",
    archive_member="sherpa-onnx-pyannote-segmentation-3-0/model.onnx",
)
# (sic) the upstream release tag really is spelled "recongition"
EMBEDDING_MODEL = ModelFile(
    url=f"{_RELEASES}/speaker-recongition-models/nemo_en_titanet_small.onnx",
    sha256="ad4a1802485d8b34c722d2a9d04249662f2ece5d28a7a039063ca22f515a789e",
    target_sha256="ad4a1802485d8b34c722d2a9d04249662f2ece5d28a7a039063ca22f515a789e",
    target="nemo_en_titanet_small.onnx",
)

Opener = Callable[[str], Any]


def default_model_dir() -> Path:
    """Where downloaded models are cached."""
    override = os.environ.get("VTT_MODEL_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "vtt-transcribe" / "models"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, dest: Path, opener: Opener) -> None:
    with opener(url) as resp, dest.open("wb") as out:
        while block := resp.read(1024 * 1024):
            out.write(block)


def _extract_member(archive: Path, member: str, dest: Path) -> None:
    """Copy exactly one regular file out of a .tar.bz2 (never extracts anything else)."""
    with tarfile.open(archive, "r:bz2") as tar:
        info = tar.getmember(member)
        if not info.isfile():
            msg = f"Unexpected entry type for {member} in model archive"
            raise RuntimeError(msg)
        src = tar.extractfile(info)
        if src is None:  # pragma: no cover - isfile() guarantees a file object
            msg = f"Cannot read {member} from model archive"
            raise RuntimeError(msg)
        with src, dest.open("wb") as out:
            while block := src.read(1024 * 1024):
                out.write(block)


def ensure_model(spec: ModelFile, model_dir: Path, opener: Opener = urllib.request.urlopen) -> Path:
    """Return the path to a verified model, downloading it first if it is missing or corrupt."""
    target = model_dir / spec.target
    if target.exists() and _sha256(target) == spec.target_sha256:
        return target

    model_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading diarization model", extra={"url": spec.url})
    print(f"Downloading speaker model (one-time): {spec.target}")
    with tempfile.TemporaryDirectory(dir=model_dir) as tmp:
        download = Path(tmp) / "download"
        _download(spec.url, download, opener)
        actual = _sha256(download)
        if actual != spec.sha256:
            msg = f"Downloaded {spec.target} failed its integrity check (expected sha256 {spec.sha256}, got {actual})."
            raise RuntimeError(msg)
        if spec.archive_member is None:
            download.replace(target)
        else:
            _extract_member(download, spec.archive_member, target)
            if _sha256(target) != spec.target_sha256:
                target.unlink()
                msg = f"Extracted {spec.target} failed its integrity check."
                raise RuntimeError(msg)
    return target


def ensure_models(model_dir: Path | None = None, opener: Opener = urllib.request.urlopen) -> tuple[Path, Path]:
    """Return (segmentation_model, embedding_model) paths, downloading them if needed."""
    directory = model_dir or default_model_dir()
    return (
        ensure_model(SEGMENTATION_MODEL, directory, opener),
        ensure_model(EMBEDDING_MODEL, directory, opener),
    )


def read_wav_mono(path: Path) -> tuple[Any, int]:
    """Read a 16-bit mono PCM WAV into a float32 numpy array in [-1, 1]. Returns (samples, rate)."""
    import numpy as np

    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            msg = "Expected 16-bit mono WAV"
            raise ValueError(msg)
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, rate


class SherpaDiarizer(SpeakerLabeler):
    """Speaker diarization using sherpa-onnx. CPU only; needs no token."""

    def __init__(
        self,
        hf_token: str | None = None,  # noqa: ARG002 - accepted for interface parity, not needed
        device: str = "auto",
        num_speakers: int | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        model_dir: Path | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Create a diarizer.

        Args:
            hf_token: Ignored. Present so this class can stand in for the pyannote backend.
            device: Ignored apart from a notice: this backend always runs on the CPU.
            num_speakers: If known, cluster to exactly this many speakers; otherwise detect.
            threshold: Clustering distance threshold used when ``num_speakers`` is not given.
            model_dir: Where models are cached. Defaults to ``~/.cache/vtt-transcribe/models``.
            progress_callback: Optional ``callback(fraction, message)``; called at step start and finish.
        """
        self.progress_callback = progress_callback
        self.device = "cpu"
        if device in ("cuda", "gpu"):
            logger.warning("The sherpa diarization backend runs on the CPU; ignoring --device %s", device)
        self.num_speakers = num_speakers
        self.threshold = threshold
        self.model_dir = model_dir
        self._engines: dict[float, Any] = {}

    def _load(self, threshold: float | None = None) -> Any:
        threshold = self.threshold if threshold is None else threshold
        if threshold not in self._engines:
            import sherpa_onnx

            segmentation, embedding = ensure_models(self.model_dir)
            config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
                segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                    pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(segmentation)),
                    num_threads=4,
                ),
                embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding), num_threads=4),
                clustering=sherpa_onnx.FastClusteringConfig(
                    num_clusters=self.num_speakers if self.num_speakers else -1,
                    threshold=threshold,
                ),
                min_duration_on=0.3,
                min_duration_off=0.5,
            )
            if not config.validate():  # pragma: no cover - only if a model file is unreadable
                msg = "Invalid sherpa-onnx diarization configuration (are the model files intact?)"
                raise RuntimeError(msg)
            self._engines[threshold] = sherpa_onnx.OfflineSpeakerDiarization(config)
        return self._engines[threshold]

    def _diarize_audio_internal(self, audio_path: Path) -> list[tuple[float, float, str]]:
        engine = self._load()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "audio.wav"
            # Any input format -> 16 kHz mono PCM, via ffmpeg (already a hard requirement of vtt).
            self._convert_to_wav(audio_path, wav_path)
            samples, rate = read_wav_mono(wav_path)
        if rate != engine.sample_rate:  # pragma: no cover - _convert_to_wav always writes 16 kHz
            msg = f"Expected {engine.sample_rate} Hz audio, got {rate} Hz"
            raise ValueError(msg)
        segments = self._segments(engine, samples)
        if self.num_speakers is None and self.threshold > RECLUSTER_THRESHOLD and len({s[2] for s in segments}) == 1:
            retry = self._segments(self._load(RECLUSTER_THRESHOLD), samples)
            if _is_real_split(retry):
                logger.info(
                    "Single speaker found; re-clustered at a lower threshold", extra={"threshold": RECLUSTER_THRESHOLD}
                )
                return retry
        return segments

    @staticmethod
    def _segments(engine: Any, samples: Any) -> list[tuple[float, float, str]]:
        result = engine.process(samples).sort_by_start_time()
        return [(float(s.start), float(s.end), f"SPEAKER_{s.speaker:02d}") for s in result]


def _is_real_split(segments: list[tuple[float, float, str]]) -> bool:
    """True if ``segments`` has 2+ speakers, enough turns, and the second-largest speaker has enough speech."""
    talk: dict[str, float] = {}
    turns: dict[str, int] = {}
    for start, end, who in segments:
        talk[who] = talk.get(who, 0.0) + end - start
        turns[who] = turns.get(who, 0) + 1
    if len(talk) < 2:
        return False
    total = sum(talk.values())
    ranked = sorted(talk, key=lambda w: talk[w], reverse=True)
    return talk[ranked[1]] >= RECLUSTER_MIN_SHARE * total and sum(turns.values()) >= RECLUSTER_MIN_TURNS
