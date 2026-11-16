"""Tests for the local faster-whisper engine (the model is mocked: no network, no downloads)."""

import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vtt_transcribe import dependencies, handlers
from vtt_transcribe.cli import create_parser
from vtt_transcribe.local_whisper import DEFAULT_MODEL, LocalTranscriber, load_audio, resolve_device, whisper_model_dir


def _fake_model() -> MagicMock:
    model = MagicMock()
    seg = SimpleNamespace
    model.transcribe.return_value = (
        iter(
            [
                seg(start=0.0, end=2.5, text=" Hello there."),
                seg(start=3.0, end=65.0, text=" Second line."),
                seg(start=66, end=67, text="  "),
            ]
        ),
        SimpleNamespace(language="en"),
    )
    model.detect_language.return_value = ("fr", 0.9, [])
    return model


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    path = tmp_path / "a.mp3"
    path.write_bytes(b"x")
    return path


def _transcriber(model: MagicMock) -> LocalTranscriber:
    t = LocalTranscriber(device="cpu")
    t._model = model
    return t


class TestLocalTranscriber:
    def test_output_matches_openai_line_format(self, audio: Path) -> None:
        model = _fake_model()
        with patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"):
            out = _transcriber(model).transcribe_audio_file(audio, language="en")
        assert out == "[00:00:00 - 00:00:02] Hello there.\n[00:00:03 - 00:01:05] Second line."
        assert model.transcribe.call_args.kwargs["language"] == "en"
        assert model.transcribe.call_args.kwargs["task"] == "transcribe"

    def test_translate_uses_translate_task(self, audio: Path) -> None:
        model = _fake_model()
        with patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"):
            _transcriber(model).translate_audio_file(audio)
        assert model.transcribe.call_args.kwargs["task"] == "translate"

    def test_detect_language_uses_first_30_seconds(self, audio: Path) -> None:
        import numpy as np

        model = _fake_model()
        with patch("vtt_transcribe.local_whisper.load_audio", return_value=np.zeros(16000 * 90, dtype=np.float32)):
            assert _transcriber(model).detect_language(audio) == "fr"
        assert len(model.detect_language.call_args.args[0]) == 16000 * 30

    def test_missing_audio_raises(self, tmp_path: Path) -> None:
        t = _transcriber(_fake_model())
        with pytest.raises(FileNotFoundError):
            t.transcribe_audio_file(tmp_path / "nope.mp3")
        with pytest.raises(FileNotFoundError):
            t.detect_language(tmp_path / "nope.mp3")

    def test_never_chunks_and_needs_no_key(self) -> None:
        t = LocalTranscriber(device="cpu")
        assert t.MAX_SIZE_MB > 10_000
        assert t.model_name == DEFAULT_MODEL
        assert t.compute_type == "int8"

    def test_model_loads_lazily_with_cache_dir(self, tmp_path: Path) -> None:
        fake_module = MagicMock()
        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            t = LocalTranscriber(model="base", device="cuda", model_dir=tmp_path / "m")
            assert t.compute_type == "int8_float16"
            t._get_model()
            t._get_model()
        fake_module.WhisperModel.assert_called_once_with(
            "base", device="cuda", compute_type="int8_float16", download_root=str(tmp_path / "m")
        )

    def test_missing_faster_whisper_gives_install_hint(self) -> None:
        with patch.dict(sys.modules, {"faster_whisper": None}), pytest.raises(ImportError, match=r"vtt-transcribe\[local\]"):
            LocalTranscriber(device="cpu")._get_model()


class TestHelpers:
    def test_model_dir_env_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("VTT_MODEL_DIR", str(tmp_path))
        assert whisper_model_dir() == tmp_path / "whisper"

    def test_model_dir_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("VTT_MODEL_DIR", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        assert whisper_model_dir() == tmp_path / "vtt-transcribe" / "models" / "whisper"

    def test_resolve_device(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISABLE_GPU", raising=False)
        assert resolve_device("gpu") == "cuda"
        assert resolve_device("cuda") == "cuda"
        assert resolve_device("cpu") == "cpu"
        ct2 = MagicMock()
        ct2.get_cuda_device_count.return_value = 1
        with patch.dict(sys.modules, {"ctranslate2": ct2}):
            assert resolve_device("auto") == "cuda"
            monkeypatch.setenv("DISABLE_GPU", "1")
            assert resolve_device("auto") == "cpu"
        monkeypatch.delenv("DISABLE_GPU")
        with patch.dict(sys.modules, {"ctranslate2": None}):
            assert resolve_device("auto") == "cpu"

    def test_load_audio_decodes_via_ffmpeg(self, audio: Path) -> None:
        import numpy as np

        pcm = np.array([0, 16384, -32768], dtype=np.int16).tobytes()
        with patch(
            "vtt_transcribe.local_whisper.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=pcm, stderr=b"")
        ):
            out = load_audio(audio)
        assert out.tolist() == [0.0, 0.5, -1.0]

    def test_load_audio_ffmpeg_failure(self, audio: Path) -> None:
        with (
            patch(
                "vtt_transcribe.local_whisper.subprocess.run",
                return_value=SimpleNamespace(returncode=1, stdout=b"", stderr=b"bad"),
            ),
            pytest.raises(RuntimeError, match="bad"),
        ):
            load_audio(audio)


class TestEngineSelection:
    def test_resolve_engine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert dependencies.resolve_engine("openai", None) == "openai"
        assert dependencies.resolve_engine("local", "k") == "local"
        with patch.object(dependencies, "local_available", return_value=True):
            assert dependencies.resolve_engine("auto", None) == "local"
            assert dependencies.resolve_engine("auto", "k") == "openai"
            monkeypatch.setenv("OPENAI_API_KEY", "k")
            assert dependencies.resolve_engine("auto", None) == "openai"
        monkeypatch.delenv("OPENAI_API_KEY")
        with patch.object(dependencies, "local_available", return_value=False):
            assert dependencies.resolve_engine("auto", None) == "openai"

    def test_check_local_dependencies_exits(self) -> None:
        with patch.object(dependencies, "local_available", return_value=False), pytest.raises(SystemExit):
            dependencies.check_local_dependencies()
        with patch.object(dependencies, "local_available", return_value=True):
            dependencies.check_local_dependencies()

    def test_cli_defaults_keep_openai(self) -> None:
        args = create_parser().parse_args(["a.mp3"])
        assert args.engine == "openai"
        assert args.model is None
        args = create_parser().parse_args(["a.mp3", "--engine", "local", "--model", "base"])
        assert (args.engine, args.model) == ("local", "base")


def _args(**kw: object) -> Namespace:
    base = {
        "input_file": "a.mp3", "engine": "local", "model": "tiny", "device": "cpu", "translate": False, "translate_to": None,
        "language": "en", "output_audio": None, "delete_audio": False, "force": False, "scan_chunks": False,
        "diarize": False, "hf_token": None, "no_review_speakers": True,
    }  # fmt: skip
    base.update(kw)
    return Namespace(**base)


class TestHandlers:
    def test_local_transcription_without_key(self, audio: Path) -> None:
        model = _fake_model()
        with (
            patch("vtt_transcribe.local_whisper.WhisperModel", create=True),
            patch("vtt_transcribe.local_whisper.LocalTranscriber._get_model", return_value=model),
            patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"),
        ):
            out = handlers.handle_standard_transcription(_args(input_file=str(audio)), None)
        assert "[00:00:00 - 00:00:02] Hello there." in out

    def test_local_diarize_applies_speakers(self, audio: Path) -> None:
        model = _fake_model()
        diarizer = MagicMock()
        diarizer.apply_speakers_to_transcript.return_value = "SPEAKER_00: hi"
        cls = MagicMock(return_value=diarizer)
        with (
            patch("vtt_transcribe.local_whisper.LocalTranscriber._get_model", return_value=model),
            patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"),
            patch.object(handlers, "_lazy_import_diarization", return_value=(cls, None, None, None)),
        ):
            out = handlers.handle_standard_transcription(_args(input_file=str(audio), diarize=True, diarizer="sherpa"), None)
        assert out == "SPEAKER_00: hi"
        diarizer.diarize_audio.assert_called_once_with(audio)

    def test_local_translate_audio(self, audio: Path) -> None:
        model = _fake_model()
        with (
            patch("vtt_transcribe.local_whisper.LocalTranscriber._get_model", return_value=model),
            patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"),
        ):
            out = handlers.handle_standard_transcription(_args(input_file=str(audio), translate=True), None)
        assert "Hello there." in out
        assert model.transcribe.call_args.kwargs["task"] == "translate"

    def test_translate_to_needs_key(self, audio: Path) -> None:
        model = _fake_model()
        with (
            patch("vtt_transcribe.local_whisper.LocalTranscriber._get_model", return_value=model),
            patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"),
            pytest.raises(ValueError, match="--translate-to"),
        ):
            handlers.handle_standard_transcription(_args(input_file=str(audio), translate_to="French"), None)

    def test_openai_engine_requires_key(self, audio: Path) -> None:
        with pytest.raises(ValueError, match="API key"):
            handlers.handle_standard_transcription(_args(input_file=str(audio), engine="openai"), None)
