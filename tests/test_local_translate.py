"""Tests for local text translation (CTranslate2/sentencepiece mocked: no network, no model)."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vtt_transcribe.local_translate import MODEL_REVISION, LocalTextTranslator, language_code, split_sentences


def test_language_code() -> None:
    assert language_code("Spanish") == "es"
    assert language_code(" french ") == "fr"
    assert language_code("zh-CN") == "zh"
    assert language_code("pt_BR") == "pt"
    assert language_code("Mandarin") == "zh"
    with pytest.raises(ValueError, match="Unsupported language"):
        language_code("Klingon")


def _translator() -> tuple[LocalTextTranslator, MagicMock, MagicMock]:
    t = LocalTextTranslator(source_language="en", device="cpu")
    sp, ct = MagicMock(), MagicMock()
    sp.encode.side_effect = lambda text, out_type=str: text.split()  # noqa: ARG005
    sp.decode.side_effect = lambda toks: " ".join(toks)
    ct.translate_batch.side_effect = (
        lambda batch, target_prefix, beam_size: [  # noqa: ARG005
            SimpleNamespace(hypotheses=[[target_prefix[0][0], *[w.upper() for w in b[1:-1]]]]) for b in batch
        ]
    )
    t._translator, t._sp = ct, sp
    return t, sp, ct


def test_keeps_timestamps_and_skips_blank_lines() -> None:
    t, _, ct = _translator()
    out = t.translate_text("[00:00:00 - 00:00:02] hello world\n\n[00:00:03 - 00:00:04] bye", "French")
    assert out == "[00:00:00 - 00:00:02] HELLO WORLD\n\n[00:00:03 - 00:00:04] BYE"
    batch = ct.translate_batch.call_args.args[0]
    assert batch[0] == ["__en__", "hello", "world", "</s>"]
    assert ct.translate_batch.call_args.kwargs["target_prefix"][0] == ["__fr__"]


def test_split_sentences() -> None:
    assert split_sentences("Hola. ¿Qué tal? Bien!") == ["Hola.", "¿Qué tal?", "Bien!"]
    assert split_sentences("a\u3002b\uff1fc") == ["a\u3002", "b\uff1f", "c"]
    assert split_sentences("no end") == ["no end"]
    assert split_sentences("   ") == []


def test_multi_sentence_lines_are_translated_per_sentence() -> None:
    t, _, ct = _translator()
    out = t.translate_text("[00:00:00 - 00:00:05] good morning all. today we talk\n[00:00:05 - 00:00:06] bye", "fr")
    assert out == "[00:00:00 - 00:00:05] GOOD MORNING ALL. TODAY WE TALK\n[00:00:05 - 00:00:06] BYE"
    batch = ct.translate_batch.call_args.args[0]
    assert batch[0] == ["__en__", "good", "morning", "all.", "</s>"]
    assert batch[1] == ["__en__", "today", "we", "talk", "</s>"]
    assert len(batch) == 3


def test_keeps_speaker_labels_only_when_asked() -> None:
    t, _, _ = _translator()
    line = "[00:00:00 - 00:00:02] SPEAKER_00: hi there"
    assert t.translate_text(line, "de", speakers=True) == "[00:00:00 - 00:00:02] SPEAKER_00: HI THERE"
    assert t.translate_text(line, "de") == "[00:00:00 - 00:00:02] SPEAKER_00: HI THERE"


def test_same_language_is_a_no_op() -> None:
    t, _, ct = _translator()
    assert t.translate_text("[00:00:00 - 00:00:02] hi", "English") == "[00:00:00 - 00:00:02] hi"
    ct.translate_batch.assert_not_called()


def test_load_downloads_pinned_revision(tmp_path: Path) -> None:
    ct2, spm, hub = MagicMock(), MagicMock(), MagicMock()
    hub.snapshot_download.return_value = str(tmp_path / "snap")
    mods = {"ctranslate2": ct2, "sentencepiece": spm, "huggingface_hub": hub}
    with patch.dict(sys.modules, mods):
        t = LocalTextTranslator(device="cuda", model_dir=tmp_path / "m")
        t._load()
        t._load()
    assert hub.snapshot_download.call_count == 1
    assert hub.snapshot_download.call_args.kwargs["revision"] == MODEL_REVISION
    ct2.Translator.assert_called_once_with(str(tmp_path / "snap"), device="cuda", compute_type="int8_float16")


def test_missing_sentencepiece_gives_install_hint(tmp_path: Path) -> None:
    with patch.dict(sys.modules, {"sentencepiece": None}), pytest.raises(ImportError, match=r"vtt-transcribe\[local\]"):
        LocalTextTranslator(device="cpu", model_dir=tmp_path)._load()
