"""Tests for speaker diarization functionality."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_speaker_diarizer_can_import_pyannote() -> None:
    """Test that pyannote.audio can be imported."""
    try:
        from pyannote.audio import Pipeline  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        pytest.fail("pyannote.audio not installed")


def test_speaker_diarizer_initialization_with_token() -> None:
    """Test SpeakerDiarizer can be initialized with a token."""
    from vtt.diarization import SpeakerDiarizer  # type: ignore[import-not-found]

    diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106
    assert diarizer.hf_token == "test_token"  # noqa: S105


def test_speaker_diarizer_initialization_from_env() -> None:
    """Test SpeakerDiarizer can be initialized from HF_TOKEN env var."""
    from vtt.diarization import SpeakerDiarizer  # type: ignore[import-not-found]

    os.environ["HF_TOKEN"] = "env_token"  # noqa: S105
    try:
        diarizer = SpeakerDiarizer()
        assert diarizer.hf_token == "env_token"  # noqa: S105
    finally:
        del os.environ["HF_TOKEN"]


def test_speaker_diarizer_initialization_no_token_raises_error() -> None:
    """Test SpeakerDiarizer raises error when no token provided."""
    from vtt.diarization import SpeakerDiarizer  # type: ignore[import-not-found]

    # Ensure HF_TOKEN is not set
    os.environ.pop("HF_TOKEN", None)

    with pytest.raises(ValueError, match="Hugging Face token not provided"):
        SpeakerDiarizer()


def test_diarize_audio_returns_speaker_segments() -> None:
    """Test diarize_audio returns list of speaker segments."""
    from vtt.diarization import SpeakerDiarizer  # type: ignore[import-not-found]

    diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

    # Mock the pipeline
    mock_turn = MagicMock()
    mock_turn.start = 0.0
    mock_turn.end = 5.0

    mock_pipeline = MagicMock()
    mock_pipeline.return_value.itertracks.return_value = [
        (mock_turn, None, "SPEAKER_00"),
    ]

    with patch("vtt.diarization.Pipeline.from_pretrained", return_value=mock_pipeline):
        audio_path = Path("/fake/audio.mp3")
        segments = diarizer.diarize_audio(audio_path)  # type: ignore[attr-defined]

        assert len(segments) == 1
        assert segments[0] == (0.0, 5.0, "SPEAKER_00")


def test_apply_speakers_to_transcript_adds_labels() -> None:
    """Test apply_speakers_to_transcript adds speaker labels to transcript."""
    from vtt.diarization import SpeakerDiarizer  # type: ignore[import-not-found]

    diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

    transcript = "[00:00 - 00:05] Hello world"
    speaker_segments = [(0.0, 5.0, "SPEAKER_00")]

    result = diarizer.apply_speakers_to_transcript(transcript, speaker_segments)  # type: ignore[attr-defined]

    assert result == "[00:00 - 00:05] SPEAKER_00: Hello world"
