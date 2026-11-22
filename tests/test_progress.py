"""Tests for the optional progress_callback API (no models, no network)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from vtt_transcribe.diarization_common import SpeakerLabeler
from vtt_transcribe.local_translate import LocalTextTranslator
from vtt_transcribe.local_whisper import LocalTranscriber
from vtt_transcribe.progress import format_clock, report
from vtt_transcribe.sherpa_diarization import SherpaDiarizer
from vtt_transcribe.transcriber import VideoTranscriber


def test_report_clamps_and_swallows_errors() -> None:
    calls: list[tuple[float, str]] = []
    report(lambda f, m: calls.append((f, m)), 1.7, "x")
    report(lambda f, m: calls.append((f, m)), -1, "y")
    report(None, 0.5, "z")

    def boom(_f: float, _m: str) -> None:
        raise RuntimeError

    report(boom, 0.5, "ignored")
    assert calls == [(1.0, "x"), (0.0, "y")]


def test_format_clock() -> None:
    assert format_clock(3725.9) == "01:02:05"
    assert format_clock(-3) == "00:00:00"


def test_local_transcriber_reports_position_over_duration(tmp_path: Path) -> None:
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"x")
    seg = SimpleNamespace
    model = MagicMock()
    model.transcribe.return_value = (
        iter([seg(start=0, end=25, text=" a"), seg(start=25, end=100, text=" b")]),
        SimpleNamespace(language="en", duration=100.0),
    )
    events: list[tuple[float, str]] = []
    t = LocalTranscriber(device="cpu", progress_callback=lambda f, m: events.append((f, m)))
    t._model = model
    with patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"):
        out = t.transcribe_audio_file(audio)
    assert out.count("\n") == 1
    assert [f for f, _ in events] == [0.0, 0.25, 1.0, 1.0]
    assert events[1][1] == "Transcribing 00:00:25 / 00:01:40"


def test_local_transcriber_without_callback_unchanged(tmp_path: Path) -> None:
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"x")
    model = MagicMock()
    model.transcribe.return_value = (iter([SimpleNamespace(start=0, end=1, text="a")]), SimpleNamespace(language="en"))
    t = LocalTranscriber(device="cpu")
    t._model = model
    with patch("vtt_transcribe.local_whisper.load_audio", return_value="pcm"):
        assert t.transcribe_audio_file(audio) == "[00:00:00 - 00:00:01] a"


def test_openai_chunks_report_per_chunk(tmp_path: Path) -> None:
    events: list[float] = []
    with patch("vtt_transcribe.transcriber.OpenAI"):
        t = VideoTranscriber("k", progress_callback=lambda f, _m: events.append(f))
    chunks = [tmp_path / "c0.mp3", tmp_path / "c1.mp3"]
    with patch.object(t, "transcribe_audio_file", return_value="[00:00:00 - 00:00:01] hi"):
        t._transcribe_chunk_files(chunks, 60.0, keep_chunks=True)
    assert events == [0.0, 0.5, 0.5, 1.0]


def test_diarization_reports_start_and_finish() -> None:
    class Fake(SpeakerLabeler):
        device = "cpu"

        def _diarize_audio_internal(self, audio_path: Path) -> list[tuple[float, float, str]]:  # noqa: ARG002
            return [(0.0, 1.0, "SPEAKER_00")]

    events: list[float] = []
    d = Fake()
    d.progress_callback = lambda f, _m: events.append(f)
    d.diarize_audio(Path("x.wav"))
    assert events == [0.0, 1.0]
    assert SherpaDiarizer(progress_callback=d.progress_callback).progress_callback is d.progress_callback


def test_translation_reports_start_and_finish() -> None:
    events: list[float] = []
    t = LocalTextTranslator(source_language="es", device="cpu", progress_callback=lambda f, _m: events.append(f))
    with patch.object(t, "_translate_lines", return_value=["hi"]):
        t.translate_text("[00:00:00 - 00:00:01] hola", "English")
    assert events == [0.0, 1.0]
