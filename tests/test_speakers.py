"""Tests for the pure speaker/export logic (ported from vtt-transcribe-server)."""

import pytest

from vtt_transcribe import speakers

TRANSCRIPT = (
    "[00:00:00 - 00:00:05] SPEAKER_00: Hello there\n"
    "[00:00:05 - 00:00:12] SPEAKER_01: Hi, how are you\n"
    "[00:00:12 - 00:00:14] SPEAKER_00: Fine\n"
    "[00:00:14 - 00:00:20] SPEAKER_02: Me too"
)


class TestSpeakerLogic:
    def test_parse_with_and_without_speaker(self) -> None:
        segs = speakers.parse_transcript("[00:01 - 00:03] hi\n[01:00:00 - 01:00:02] SPEAKER_03: yo\nnoise")
        assert segs[0] == {"start": 1, "end": 3, "text": "hi", "speaker": None}
        assert segs[1]["start"] == 3600
        assert segs[1]["speaker"] == "SPEAKER_03"

    def test_default_and_display_names(self) -> None:
        assert speakers.default_name("SPEAKER_00") == "Speaker 1"
        assert speakers.display_name("SPEAKER_01", {"SPEAKER_01": "  Bob "}) == "Bob"
        assert speakers.display_name(None, {}) is None

    def test_summarize_orders_by_appearance_and_caps_samples(self) -> None:
        info = speakers.summarize(speakers.parse_transcript(TRANSCRIPT), {})
        assert [s["id"] for s in info] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]
        assert info[1]["seconds"] == 7
        assert info[1]["samples"] == [{"start": 5, "end": 12}]
        assert info[0]["sample_text"] == "Hello there"

    def test_merge_split_rename_roundtrip(self) -> None:
        segs = speakers.parse_transcript(TRANSCRIPT)
        merged, names = speakers.merge(segs, {"SPEAKER_02": "X", "SPEAKER_00": "Al"}, ["SPEAKER_02"], "SPEAKER_00")
        assert speakers.speaker_ids(merged) == ["SPEAKER_00", "SPEAKER_01"]
        assert names == {"SPEAKER_00": "Al"}
        split, new_id = speakers.split(merged, "SPEAKER_00", [3])
        assert new_id == "SPEAKER_02"
        assert split[3]["speaker"] == "SPEAKER_02"
        assert split[0]["speaker"] == "SPEAKER_00"

    @pytest.mark.parametrize(
        "call",
        [
            lambda s: speakers.merge(s, {}, ["SPEAKER_00"], "SPEAKER_00"),
            lambda s: speakers.merge(s, {}, ["NOPE"], "SPEAKER_00"),
            lambda s: speakers.split(s, "SPEAKER_01", [0]),  # segment 0 is not SPEAKER_01
            lambda s: speakers.split(s, "SPEAKER_01", [1]),  # would take every segment of the speaker
            lambda s: speakers.split(s, "SPEAKER_00", []),
            lambda s: speakers.rename(s, {}, "NOPE", "x"),
        ],
    )
    def test_invalid_operations_raise(self, call):
        with pytest.raises(speakers.SpeakerError):
            call(speakers.parse_transcript(TRANSCRIPT))

    def test_blank_name_clears(self) -> None:
        segs = speakers.parse_transcript(TRANSCRIPT)
        assert speakers.rename(segs, {"SPEAKER_00": "A"}, "SPEAKER_00", " ") == {}

    def test_exports_use_name_colon_text(self) -> None:
        segs = speakers.labelled(speakers.parse_transcript(TRANSCRIPT), {"SPEAKER_00": "Alice"})
        assert speakers.to_txt(segs).splitlines()[0] == "Alice: Hello there"
        assert "Alice: Hello there" in speakers.to_srt(segs)
        assert "00:00:05,000 --> 00:00:12,000" in speakers.to_srt(segs)
        assert "<v Alice>Hello there" in speakers.to_vtt(segs)
        assert speakers.to_result(segs).splitlines()[1] == "[00:00:05 - 00:00:12] Speaker 2: Hi, how are you"


class TestMore:
    def test_invalid_operations_message(self) -> None:
        with pytest.raises(speakers.SpeakerError, match="Unknown speaker"):
            speakers.rename(speakers.parse_transcript(TRANSCRIPT), {}, "NOPE", "x")

    def test_turns_to_segments(self) -> None:
        assert speakers.turns_to_segments([(0.0, 1.5, "SPEAKER_00")]) == [
            {"start": 0.0, "end": 1.5, "text": "", "speaker": "SPEAKER_00"}
        ]

    def test_sample_cap_and_unlabelled_exports(self) -> None:
        segs = [
            {"start": 0.0, "end": 30.0, "text": "long", "speaker": "SPEAKER_00"},
            {"start": 31.0, "end": 32.0, "text": " a  b ", "speaker": None},
        ]
        assert speakers.summarize(segs, {})[0]["samples"] == [{"start": 0.0, "end": 8.0}]
        assert speakers.to_txt(segs).splitlines()[1] == "a b"
        assert speakers.to_vtt(segs).count("<v") == 1
        assert speakers.default_name("custom") == "custom"

    def test_labelled_prefers_translation(self) -> None:
        segs = [{"start": 0, "end": 1, "text": "hi", "speaker": "SPEAKER_00", "translation": "hola"}]
        assert speakers.labelled(segs, {}, translated=True)[0]["text"] == "hola"
        assert speakers.labelled(segs, {})[0]["text"] == "hi"

    def test_translate_segments_keeps_speakers(self) -> None:
        segs = speakers.parse_transcript(TRANSCRIPT)
        seen: list[str] = []

        def fake(text: str) -> str:
            seen.append(text)
            return text.upper()

        out = speakers.translate_segments(segs, fake)
        assert "SPEAKER" not in seen[0]
        assert [s["speaker"] for s in out] == [s["speaker"] for s in segs]
        assert out[0]["translation"] == "HELLO THERE"
        assert "translation" not in segs[0]

    def test_translate_segments_line_mismatch(self) -> None:
        with pytest.raises(speakers.SpeakerError, match="lines"):
            speakers.translate_segments(speakers.parse_transcript(TRANSCRIPT), lambda _t: "[00:00:00 - 00:00:01] x")
