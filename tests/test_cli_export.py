"""Tests for CLI export wiring: --format, --speaker-name and .srt/.vtt save paths."""

from pathlib import Path

import pytest

from vtt_transcribe.cli import create_parser
from vtt_transcribe.handlers import save_transcript
from vtt_transcribe.main import _export_format, _output_result, _parse_speaker_names, _render_export

TRANSCRIPT = "[00:00:00 - 00:00:05] SPEAKER_00: Hello there\n[00:00:05 - 00:00:12] SPEAKER_01: Hi"


def test_parse_speaker_names() -> None:
    assert _parse_speaker_names(None) == {}
    assert _parse_speaker_names([" SPEAKER_00 = Alice ", "SPEAKER_01=Bob=Jr"]) == {
        "SPEAKER_00": "Alice",
        "SPEAKER_01": "Bob=Jr",
    }
    for bad in ("SPEAKER_00", "=x", "SPEAKER_00="):
        with pytest.raises(ValueError, match="expected ID=NAME"):
            _parse_speaker_names([bad])


def test_export_format_follows_extension() -> None:
    assert _export_format("vtt", "a.srt") == "vtt"
    assert _export_format(None, "a.SRT") == "srt"
    assert _export_format(None, "a.vtt") == "vtt"
    assert _export_format(None, "a.txt") == "txt"
    assert _export_format(None, None) == "txt"


def test_render_defaults_and_formats() -> None:
    assert _render_export(TRANSCRIPT, "txt", {}) == TRANSCRIPT
    named = _render_export(TRANSCRIPT, "txt", {"SPEAKER_00": "Alice"})
    assert named.splitlines() == ["[00:00:00 - 00:00:05] Alice: Hello there", "[00:00:05 - 00:00:12] Speaker 2: Hi"]
    assert "00:00:00,000 --> 00:00:05,000\nAlice: Hello there" in _render_export(TRANSCRIPT, "srt", {"SPEAKER_00": "Alice"})
    assert _render_export(TRANSCRIPT, "vtt", {}).startswith(
        "WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.000\n<v Speaker 1>Hello there"
    )


def test_render_unknown_speaker_and_plain_text() -> None:
    with pytest.raises(ValueError, match="SPEAKER_09"):
        _render_export(TRANSCRIPT, "txt", {"SPEAKER_09": "X"})
    assert _render_export("just text", "srt", {}) == "just text"


def test_output_result_writes_srt(tmp_path: Path) -> None:
    out = tmp_path / "talk.srt"
    _output_result(TRANSCRIPT, stdin_mode=False, save_path=str(out), speaker_names={"SPEAKER_01": "Bob"})
    assert out.read_text().startswith("1\n00:00:00,000 --> 00:00:05,000\nSpeaker 1: Hello there")
    assert "Bob: Hi" in out.read_text()


def test_stdin_mode_format_goes_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    _output_result(TRANSCRIPT, stdin_mode=True, save_path=None, fmt="vtt")
    assert capsys.readouterr().out.startswith("WEBVTT")


def test_save_transcript_keeps_subtitle_suffixes(tmp_path: Path) -> None:
    save_transcript(tmp_path / "a.vtt", "x")
    save_transcript(tmp_path / "b.md", "x")
    assert (tmp_path / "a.vtt").exists()
    assert (tmp_path / "b.txt").exists()


def test_parser_options() -> None:
    args = create_parser().parse_args(["a.mp3", "--format", "srt", "--speaker-name", "A=B", "--speaker-name", "C=D"])
    assert args.format == "srt"
    assert args.speaker_name == ["A=B", "C=D"]
