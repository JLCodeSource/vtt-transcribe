"""Tests for the sherpa-onnx diarization backend (no real models or sherpa-onnx needed)."""

import hashlib
import io
import sys
import tarfile
import types
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from vtt_transcribe import sherpa_diarization as sd
from vtt_transcribe.dependencies import check_diarization_dependencies, resolve_diarizer
from vtt_transcribe.sherpa_diarization import ModelFile, SherpaDiarizer


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Resp(io.BytesIO):
    """Minimal urlopen() response usable as a context manager."""


def _opener(payloads: dict[str, bytes]) -> Callable[[str], Any]:
    calls: list[str] = []

    def opener(url: str) -> _Resp:
        calls.append(url)
        return _Resp(payloads[url])

    opener.calls = calls  # type: ignore[attr-defined]
    return opener


def _tar_bz2(members: dict[str, bytes], *, directory: str | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:bz2") as tar:
        if directory:
            info = tarfile.TarInfo(directory)
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _wav(path: Path, *, rate: int = 16000, channels: int = 1, width: int = 2, frames: int = 1600) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"\x00" * frames * channels * width)


class TestModelDir:
    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VTT_MODEL_DIR", "/custom/models")
        assert sd.default_model_dir() == Path("/custom/models")

    def test_xdg_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VTT_MODEL_DIR", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", "/xdg")
        assert sd.default_model_dir() == Path("/xdg/vtt-transcribe/models")

    def test_home_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VTT_MODEL_DIR", raising=False)
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        assert sd.default_model_dir() == Path.home() / ".cache" / "vtt-transcribe" / "models"


class TestEnsureModel:
    def test_downloads_plain_file_and_verifies(self, tmp_path: Path) -> None:
        data = b"onnx-bytes"
        spec = ModelFile(url="http://x/m.onnx", sha256=_sha(data), target_sha256=_sha(data), target="m.onnx")
        opener = _opener({spec.url: data})
        path = sd.ensure_model(spec, tmp_path, opener)
        assert path.read_bytes() == data
        assert opener.calls == [spec.url]  # type: ignore[attr-defined]
        # second call is served from the cache with no network
        assert sd.ensure_model(spec, tmp_path, opener) == path
        assert opener.calls == [spec.url]  # type: ignore[attr-defined]

    def test_rejects_bad_download_and_keeps_nothing(self, tmp_path: Path) -> None:
        spec = ModelFile(url="http://x/m.onnx", sha256=_sha(b"good"), target_sha256=_sha(b"good"), target="m.onnx")
        with pytest.raises(RuntimeError, match="integrity check"):
            sd.ensure_model(spec, tmp_path, _opener({spec.url: b"tampered"}))
        assert not (tmp_path / "m.onnx").exists()

    def test_redownloads_a_corrupt_cached_file(self, tmp_path: Path) -> None:
        data = b"good"
        spec = ModelFile(url="http://x/m.onnx", sha256=_sha(data), target_sha256=_sha(data), target="m.onnx")
        (tmp_path / "m.onnx").write_bytes(b"corrupt")
        sd.ensure_model(spec, tmp_path, _opener({spec.url: data}))
        assert (tmp_path / "m.onnx").read_bytes() == data

    def test_extracts_one_member_from_archive(self, tmp_path: Path) -> None:
        inner = b"segmentation-model"
        archive = _tar_bz2({"pkg/model.onnx": inner, "pkg/evil.py": b"print(1)"}, directory="pkg")
        spec = ModelFile(
            url="http://x/a.tar.bz2",
            sha256=_sha(archive),
            target_sha256=_sha(inner),
            target="seg.onnx",
            archive_member="pkg/model.onnx",
        )
        path = sd.ensure_model(spec, tmp_path, _opener({spec.url: archive}))
        assert path.read_bytes() == inner
        # nothing else from the archive is written, and no temp files are left behind
        assert sorted(p.name for p in tmp_path.iterdir()) == ["seg.onnx"]

    def test_archive_member_that_is_not_a_file_is_refused(self, tmp_path: Path) -> None:
        archive = _tar_bz2({}, directory="pkg/model.onnx")
        spec = ModelFile(
            url="http://x/a.tar.bz2",
            sha256=_sha(archive),
            target_sha256="0" * 64,
            target="seg.onnx",
            archive_member="pkg/model.onnx",
        )
        with pytest.raises(RuntimeError, match="Unexpected entry type"):
            sd.ensure_model(spec, tmp_path, _opener({spec.url: archive}))

    def test_extracted_file_with_wrong_hash_is_removed(self, tmp_path: Path) -> None:
        archive = _tar_bz2({"pkg/model.onnx": b"other"})
        spec = ModelFile(
            url="http://x/a.tar.bz2",
            sha256=_sha(archive),
            target_sha256=_sha(b"expected"),
            target="seg.onnx",
            archive_member="pkg/model.onnx",
        )
        with pytest.raises(RuntimeError, match="Extracted"):
            sd.ensure_model(spec, tmp_path, _opener({spec.url: archive}))
        assert not (tmp_path / "seg.onnx").exists()

    def test_ensure_models_returns_both_paths(self, tmp_path: Path) -> None:
        with patch.object(sd, "ensure_model", side_effect=[tmp_path / "a", tmp_path / "b"]) as m:
            assert sd.ensure_models(tmp_path) == (tmp_path / "a", tmp_path / "b")
        assert [c.args[0] for c in m.call_args_list] == [sd.SEGMENTATION_MODEL, sd.EMBEDDING_MODEL]

    def test_ensure_models_uses_default_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VTT_MODEL_DIR", str(tmp_path))
        with patch.object(sd, "ensure_model", return_value=tmp_path / "x") as m:
            sd.ensure_models()
        assert m.call_args.args[1] == tmp_path

    def test_pinned_models_point_at_the_official_releases(self) -> None:
        assert sd.SEGMENTATION_MODEL.url.startswith("https://github.com/k2-fsa/sherpa-onnx/releases/download/")
        assert sd.EMBEDDING_MODEL.url.startswith("https://github.com/k2-fsa/sherpa-onnx/releases/download/")
        for spec in (sd.SEGMENTATION_MODEL, sd.EMBEDDING_MODEL):
            assert len(spec.sha256) == 64
            assert len(spec.target_sha256) == 64


class TestReadWav:
    def test_reads_16bit_mono(self, tmp_path: Path) -> None:
        p = tmp_path / "a.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(np.array([0, 16384, -32768], dtype=np.int16).tobytes())
        samples, rate = sd.read_wav_mono(p)
        assert rate == 16000
        assert samples.dtype == np.float32
        assert samples.tolist() == [0.0, 0.5, -1.0]

    @pytest.mark.parametrize(("channels", "width"), [(2, 2), (1, 1)])
    def test_rejects_other_formats(self, tmp_path: Path, channels: int, width: int) -> None:
        p = tmp_path / "a.wav"
        _wav(p, channels=channels, width=width)
        with pytest.raises(ValueError, match="16-bit mono"):
            sd.read_wav_mono(p)


class _FakeSegment:
    def __init__(self, start: float, end: float, speaker: int) -> None:
        self.start, self.end, self.speaker = start, end, speaker


class _FakeResult:
    def __init__(self, segs: list[_FakeSegment]) -> None:
        self._segs = segs

    def sort_by_start_time(self) -> list[_FakeSegment]:
        return sorted(self._segs, key=lambda s: s.start)


def _fake_sherpa(segs: list[_FakeSegment], *, valid: bool = True) -> types.ModuleType:
    mod = types.ModuleType("sherpa_onnx")
    configs: list[Any] = []

    def ns(name: str) -> Callable[..., Any]:
        def make(**kw: Any) -> types.SimpleNamespace:
            return types.SimpleNamespace(_name=name, **kw)

        return make

    class Config:
        def __init__(self, **kw: Any) -> None:
            self.kw = kw
            configs.append(self)

        def validate(self) -> bool:
            return valid

    class Engine:
        sample_rate = 16000

        def __init__(self, config: Config) -> None:
            self.config = config
            self.processed: Any = None

        def process(self, samples: Any) -> _FakeResult:
            self.processed = samples
            return _FakeResult(segs)

    mod.OfflineSpeakerDiarizationConfig = Config  # type: ignore[attr-defined]
    mod.OfflineSpeakerSegmentationModelConfig = ns("segmodel")  # type: ignore[attr-defined]
    mod.OfflineSpeakerSegmentationPyannoteModelConfig = ns("pyannote")  # type: ignore[attr-defined]
    mod.SpeakerEmbeddingExtractorConfig = ns("emb")  # type: ignore[attr-defined]
    mod.FastClusteringConfig = ns("cluster")  # type: ignore[attr-defined]
    mod.OfflineSpeakerDiarization = Engine  # type: ignore[attr-defined]
    mod.configs = configs  # type: ignore[attr-defined]
    return mod


class TestSherpaDiarizer:
    def test_defaults_and_gpu_notice(self) -> None:
        d = SherpaDiarizer()
        assert d.device == "cpu"
        assert d.threshold == sd.DEFAULT_THRESHOLD
        with patch.object(sd.logger, "warning") as warn:
            SherpaDiarizer(device="cuda")
        warn.assert_called_once()

    def test_needs_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HF_TOKEN", raising=False)
        SherpaDiarizer(hf_token=None)  # does not raise

    def test_diarizes_and_labels_speakers(self, tmp_path: Path) -> None:
        fake = _fake_sherpa([_FakeSegment(5.0, 8.0, 1), _FakeSegment(0.0, 4.5, 0)])
        d = SherpaDiarizer(model_dir=tmp_path, num_speakers=2, threshold=0.7)

        def convert(_self: Any, _src: Path, dest: Path) -> None:
            _wav(dest)

        with (
            patch.dict(sys.modules, {"sherpa_onnx": fake}),
            patch.object(sd, "ensure_models", return_value=(tmp_path / "seg.onnx", tmp_path / "emb.onnx")),
            patch.object(SherpaDiarizer, "_convert_to_wav", convert),
        ):
            segments = d.diarize_audio(tmp_path / "talk.mp3")

        assert segments == [(0.0, 4.5, "SPEAKER_00"), (5.0, 8.0, "SPEAKER_01")]
        cfg = fake.configs[0].kw  # type: ignore[attr-defined]
        assert cfg["clustering"].num_clusters == 2
        assert cfg["clustering"].threshold == 0.7
        assert cfg["segmentation"].pyannote.model == str(tmp_path / "seg.onnx")
        assert cfg["embedding"].model == str(tmp_path / "emb.onnx")

    def test_auto_speaker_count_uses_minus_one(self, tmp_path: Path) -> None:
        fake = _fake_sherpa([])
        d = SherpaDiarizer(model_dir=tmp_path)
        with (
            patch.dict(sys.modules, {"sherpa_onnx": fake}),
            patch.object(sd, "ensure_models", return_value=(tmp_path / "s", tmp_path / "e")),
        ):
            d._load()
        assert fake.configs[0].kw["clustering"].num_clusters == -1  # type: ignore[attr-defined]

    def test_engine_is_built_once(self, tmp_path: Path) -> None:
        fake = _fake_sherpa([])
        d = SherpaDiarizer(model_dir=tmp_path)
        with (
            patch.dict(sys.modules, {"sherpa_onnx": fake}),
            patch.object(sd, "ensure_models", return_value=(tmp_path / "s", tmp_path / "e")) as ensure,
        ):
            assert d._load() is d._load()
        ensure.assert_called_once()

    def test_wav_conversion_failure_propagates(self, tmp_path: Path) -> None:
        fake = _fake_sherpa([])
        d = SherpaDiarizer(model_dir=tmp_path)
        proc = MagicMock(returncode=1, stderr="bad input")
        with (
            patch.dict(sys.modules, {"sherpa_onnx": fake}),
            patch.object(sd, "ensure_models", return_value=(tmp_path / "s", tmp_path / "e")),
            patch("subprocess.run", return_value=proc),
            pytest.raises(RuntimeError, match="Failed to convert to WAV"),
        ):
            d._diarize_audio_internal(tmp_path / "x.mp3")

    def test_labels_a_transcript(self) -> None:
        d = SherpaDiarizer()
        out = d.apply_speakers_to_transcript("[00:00:00 - 00:00:04] Hello", [(0.0, 5.0, "SPEAKER_00")])
        assert out == "[00:00:00 - 00:00:04] SPEAKER_00: Hello"

    def test_default_base_class_method_is_abstract(self) -> None:
        from vtt_transcribe.diarization_common import SpeakerLabeler

        with pytest.raises(NotImplementedError):
            SpeakerLabeler()._diarize_audio_internal(Path("x"))


class TestBackendSelection:
    def test_explicit_choice_wins(self) -> None:
        assert resolve_diarizer("pyannote") == "pyannote"
        assert resolve_diarizer("sherpa") == "sherpa"

    def test_auto_prefers_sherpa_when_installed(self) -> None:
        with patch("vtt_transcribe.dependencies.find_spec", return_value=object()):
            assert resolve_diarizer("auto") == "sherpa"

    def test_auto_falls_back_to_pyannote(self) -> None:
        def spec(name: str) -> object | None:
            return None if name in ("sherpa_onnx", "numpy") else object()

        with patch("vtt_transcribe.dependencies.find_spec", side_effect=spec):
            assert resolve_diarizer("auto") == "pyannote"

    def test_sherpa_check_names_the_extra(self, capsys: pytest.CaptureFixture) -> None:
        with (
            patch("vtt_transcribe.dependencies.find_spec", return_value=None),
            pytest.raises(SystemExit),
        ):
            check_diarization_dependencies("sherpa")
        err = capsys.readouterr().err
        assert "sherpa_onnx" in err
        assert "vtt-transcribe[sherpa]" in err

    def test_sherpa_check_passes_without_torch(self) -> None:
        def spec(name: str) -> object | None:
            return None if name in ("torch", "torchaudio", "pyannote.audio") else object()

        with patch("vtt_transcribe.dependencies.find_spec", side_effect=spec):
            check_diarization_dependencies("sherpa")
            check_diarization_dependencies("auto")

    def test_auto_check_passes_with_only_pyannote(self) -> None:
        def spec(name: str) -> object | None:
            return None if name in ("sherpa_onnx", "numpy") else object()

        with patch("vtt_transcribe.dependencies.find_spec", side_effect=spec):
            check_diarization_dependencies("auto")

    def test_auto_check_fails_when_neither_is_installed(self, capsys: pytest.CaptureFixture) -> None:
        with (
            patch("vtt_transcribe.dependencies.find_spec", return_value=None),
            pytest.raises(SystemExit),
        ):
            check_diarization_dependencies("auto")
        err = capsys.readouterr().err
        assert "vtt-transcribe[sherpa]" in err
        assert "vtt-transcribe[diarization]" in err


class TestHandlersWithSherpa:
    def test_lazy_import_returns_sherpa_classes_without_torch(self) -> None:
        from vtt_transcribe.handlers import _lazy_import_diarization

        cls, fmt, uniq, ctx = _lazy_import_diarization("sherpa")
        assert cls is SherpaDiarizer
        assert callable(fmt)
        assert callable(uniq)
        assert callable(ctx)

    def test_lazy_import_wraps_import_errors(self) -> None:
        from vtt_transcribe.handlers import DIARIZATION_DEPS_ERROR_MSG, _lazy_import_diarization

        with (
            patch.dict(sys.modules, {"vtt_transcribe.sherpa_diarization": None}),
            pytest.raises(ImportError, match="Diarization dependencies not installed") as exc,
        ):
            _lazy_import_diarization("sherpa")
        assert str(exc.value) == DIARIZATION_DEPS_ERROR_MSG

    def test_build_diarizer_passes_num_speakers_only_to_sherpa(self) -> None:
        from vtt_transcribe.handlers import _build_diarizer

        cls = MagicMock()
        _build_diarizer(cls, "sherpa", "tok", "cpu", 3)
        cls.assert_called_once_with(hf_token="tok", device="cpu", num_speakers=3)
        cls.reset_mock()
        _build_diarizer(cls, "pyannote", "tok", "cpu", 3)
        cls.assert_called_once_with(hf_token="tok", device="cpu")

    def test_diarize_only_with_sherpa_never_imports_torch(self, tmp_path: Path) -> None:
        from vtt_transcribe.handlers import handle_diarize_only_mode

        audio = tmp_path / "a.wav"
        audio.touch()
        diarizer = MagicMock()
        diarizer.diarize_audio.return_value = [(0.0, 2.0, "SPEAKER_00")]
        cls = MagicMock(return_value=diarizer)
        fmt = MagicMock(return_value="[00:00 - 00:02] SPEAKER_00")
        with (
            patch("vtt_transcribe.handlers._lazy_import_diarization", return_value=(cls, fmt, None, None)),
            patch.dict(sys.modules, {"torch": None}),  # an `import torch` would raise
            patch("builtins.print"),
        ):
            out = handle_diarize_only_mode(audio, None, None, "cuda", "sherpa", 2)
        assert out == "[00:00 - 00:02] SPEAKER_00"
        cls.assert_called_once_with(hf_token=None, device="cuda", num_speakers=2)

    def test_apply_diarization_with_sherpa(self, tmp_path: Path) -> None:
        from vtt_transcribe.handlers import handle_apply_diarization_mode

        audio, transcript = tmp_path / "a.wav", tmp_path / "t.txt"
        audio.touch()
        transcript.write_text("[00:00:00 - 00:00:02] hi")
        diarizer = MagicMock()
        diarizer.diarize_audio.return_value = [(0.0, 2.0, "SPEAKER_00")]
        diarizer.apply_speakers_to_transcript.return_value = "labelled"
        cls = MagicMock(return_value=diarizer)
        with (
            patch("vtt_transcribe.handlers._lazy_import_diarization", return_value=(cls, None, None, None)),
            patch("builtins.print"),
        ):
            assert handle_apply_diarization_mode(audio, transcript, None, None, "auto", "sherpa", 4) == "labelled"
        cls.assert_called_once_with(hf_token=None, device="auto", num_speakers=4)

    def test_review_loads_transcript_through_the_chosen_backend(self, tmp_path: Path) -> None:
        from vtt_transcribe.handlers import handle_review_speakers

        audio = tmp_path / "a.wav"
        audio.touch()
        diarizer = MagicMock()
        diarizer.diarize_audio.return_value = [(0.0, 2.0, "SPEAKER_00")]
        cls = MagicMock(return_value=diarizer)
        fmt = MagicMock(return_value="[00:00 - 00:02] SPEAKER_00: hi")
        ctx = MagicMock(return_value=["context"])
        with (
            patch("vtt_transcribe.handlers._lazy_import_diarization", return_value=(cls, fmt, None, ctx)) as lazy,
            patch("builtins.input", return_value=""),
            patch("builtins.print"),
        ):
            handle_review_speakers(input_path=audio, backend="sherpa", num_speakers=2)
        lazy.assert_called_with("sherpa")
        cls.assert_called_once_with(hf_token=None, device="auto", num_speakers=2)

    def test_cli_flags(self) -> None:
        from vtt_transcribe.cli import create_parser

        parser = create_parser()
        defaults = parser.parse_args(["a.mp3", "--diarize"])
        assert defaults.diarizer == "auto"
        assert defaults.num_speakers is None
        args = parser.parse_args(["a.mp3", "--diarize", "--diarizer", "sherpa", "--num-speakers", "3"])
        assert (args.diarizer, args.num_speakers) == ("sherpa", 3)
        with pytest.raises(SystemExit):
            parser.parse_args(["a.mp3", "--diarizer", "bogus"])

    def test_standard_workflow_passes_backend_to_diarizer(self, tmp_path: Path) -> None:
        from argparse import Namespace

        from vtt_transcribe.handlers import handle_standard_transcription
        from vtt_transcribe.transcriber import VideoTranscriber

        audio = tmp_path / "a.mp3"
        audio.touch()
        args = Namespace(
            input_file=str(audio), output_audio=None, delete_audio=False, force=False, scan_chunks=False,
            language=None, translate=False, translate_to=None, diarize=True, hf_token=None, device="cpu",
            no_review_speakers=True, diarizer="sherpa", num_speakers=2, save_transcript=None,
        )  # fmt: skip
        diarizer = MagicMock()
        diarizer.diarize_audio.return_value = []
        diarizer.apply_speakers_to_transcript.return_value = "done"
        cls = MagicMock(return_value=diarizer)
        with (
            patch("vtt_transcribe.handlers._lazy_import_diarization", return_value=(cls, None, None, None)) as lazy,
            patch.object(VideoTranscriber, "transcribe", return_value="text"),
            patch.object(VideoTranscriber, "detect_language", return_value="en"),
            patch("builtins.print"),
        ):
            assert handle_standard_transcription(args, "key") == "done"
        lazy.assert_called_with("sherpa")
        cls.assert_called_once_with(hf_token=None, device="cpu", num_speakers=2)


class TestSingleSpeakerRecluster:
    ONE: ClassVar = [(0.0, 5.0, "SPEAKER_00"), (6.0, 12.0, "SPEAKER_00")]
    TWO: ClassVar = [(0.0, 5.0, "SPEAKER_00"), (6.0, 12.0, "SPEAKER_01"), (13.0, 17.0, "SPEAKER_00")]

    def _run(self, tmp_path: Path, d: SherpaDiarizer, passes: list[list[tuple[float, float, str]]]) -> tuple[Any, MagicMock]:
        loaded: list[float | None] = []

        def load(threshold: float | None = None) -> MagicMock:
            loaded.append(threshold)
            return MagicMock(sample_rate=16000)

        def convert(_self: Any, _src: Path, dest: Path) -> None:
            _wav(dest)

        with (
            patch.object(SherpaDiarizer, "_load", side_effect=load),
            patch.object(SherpaDiarizer, "_segments", side_effect=passes) as seg,
            patch.object(SherpaDiarizer, "_convert_to_wav", convert),
        ):
            out = d._diarize_audio_internal(tmp_path / "x.mp3")
        return out, seg

    def test_collapsed_result_is_reclustered(self, tmp_path: Path) -> None:
        out, seg = self._run(tmp_path, SherpaDiarizer(), [self.ONE, self.TWO])
        assert out == self.TWO
        assert seg.call_count == 2

    def test_unreal_split_is_rejected(self, tmp_path: Path) -> None:
        tiny = [*self.ONE, (30.0, 30.4, "SPEAKER_01")]
        out, _ = self._run(tmp_path, SherpaDiarizer(), [self.ONE, tiny])
        assert out == self.ONE

    def test_still_one_speaker_stays(self, tmp_path: Path) -> None:
        out, _ = self._run(tmp_path, SherpaDiarizer(), [self.ONE, self.ONE])
        assert out == self.ONE

    def test_multiple_speakers_not_reclustered(self, tmp_path: Path) -> None:
        out, seg = self._run(tmp_path, SherpaDiarizer(), [self.TWO])
        assert out == self.TWO
        assert seg.call_count == 1

    def test_explicit_num_speakers_and_low_threshold_unchanged(self, tmp_path: Path) -> None:
        for d in (SherpaDiarizer(num_speakers=2), SherpaDiarizer(threshold=0.9)):
            out, seg = self._run(tmp_path, d, [self.ONE])
            assert out == self.ONE
            assert seg.call_count == 1
