"""Tests for new v0.3.0b4 features: video format detection and MP3 encoding fallback."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestVideoFormatDetection:
    """Test video format detection from binary magic bytes."""

    def test_detect_mp4_format(self) -> None:
        """Test MP4 format detection from ftyp signature."""
        from vtt_transcribe.main import _detect_format_from_data

        # MP4 file with ftyp signature
        data = b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".mp4"

    def test_detect_m4a_format(self) -> None:
        """Test M4A format detection."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".mp4"

    def test_detect_mov_format(self) -> None:
        """Test MOV/QuickTime format detection."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"\x00\x00\x00\x20ftypqt  \x00\x00\x00\x00" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".mp4"

    def test_detect_avi_format(self) -> None:
        """Test AVI format detection from RIFF+AVI signature."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"RIFF\x00\x00\x00\x00AVI \x00\x00\x00\x00" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".avi"

    def test_detect_webm_format(self) -> None:
        """Test WebM/MKV format detection from EBML signature."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".webm"

    def test_detect_mp3_id3_format(self) -> None:
        """Test MP3 format detection from ID3 tag."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"ID3\x03\x00\x00\x00" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".mp3"

    def test_detect_mp3_sync_format(self) -> None:
        """Test MP3 format detection from MPEG sync byte."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"\xff\xfb" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".mp3"

    def test_detect_wav_format(self) -> None:
        """Test WAV format detection from RIFF+WAVE signature."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".wav"

    def test_detect_ogg_format(self) -> None:
        """Test OGG format detection from OggS signature."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"OggS\x00\x02\x00\x00" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".ogg"

    def test_detect_unknown_format_defaults_to_mp3(self) -> None:
        """Test that unknown formats default to .mp3."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"UNKNOWN_FORMAT_DATA" + b"\x00" * 100
        assert _detect_format_from_data(data) == ".mp3"

    def test_detect_format_with_short_data(self) -> None:
        """Test format detection with less than 12 bytes (should default to mp3)."""
        from vtt_transcribe.main import _detect_format_from_data

        data = b"short"
        assert _detect_format_from_data(data) == ".mp3"


class TestWAVConversionFallback:
    """Test automatic WAV conversion when MP3 encoding causes issues."""

    def test_wav_conversion_triggered_by_sample_mismatch(self) -> None:
        """Test that sample mismatch error with duration >= 9.5s triggers WAV conversion."""
        from vtt_transcribe.diarization import SpeakerDiarizer

        diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".mp3", delete=False) as f:
            audio_path = Path(f.name)
            f.write(b"fake_mp3_data")

        try:
            # Tracks method calls
            calls = []

            def mock_internal(_self: object, path: Path) -> list:
                calls.append(str(path))
                # First call raises MP3 encoding error (duration >= 9.5s, so conversion triggered)
                if len(calls) == 1:
                    # Simulate the processed error message from _diarize_audio_internal
                    msg = (
                        "Audio file sample mismatch error. This usually indicates:\n"
                        "  - MP3 encoding imprecision (metadata doesn't match exact sample count)\n"
                        "  - File corruption or incomplete download\n"
                        "Expected 10.00s (441000 samples), but got 9.97s (439895 samples)."
                    )
                    raise ValueError(msg)
                # Second call (with WAV) succeeds
                return [(0.0, 10.0, "SPEAKER_00")]

            def mock_convert(_self: object, _input_path: Path, output_path: Path) -> None:
                # Create the WAV file
                output_path.write_bytes(b"fake_wav_data")

            with (
                patch.object(SpeakerDiarizer, "_diarize_audio_internal", mock_internal),
                patch.object(SpeakerDiarizer, "_convert_to_wav", mock_convert),
            ):
                result = diarizer.diarize_audio(audio_path)

            # Should have called internal twice: MP3 then WAV
            assert len(calls) == 2
            assert calls[0].endswith(".mp3")
            assert calls[1].endswith(".wav")
            assert result == [(0.0, 10.0, "SPEAKER_00")]

            # WAV should be cleaned up
            wav_path = audio_path.with_suffix(".wav")
            assert not wav_path.exists()

        finally:
            if audio_path.exists():
                audio_path.unlink()

    def test_wav_conversion_cleanup_on_retry_failure(self) -> None:
        """Test that WAV file is cleaned up even when retry fails."""
        from vtt_transcribe.diarization import SpeakerDiarizer

        diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".mp3", delete=False) as f:
            audio_path = Path(f.name)
            f.write(b"fake_mp3_data")

        try:

            def mock_internal(_self: object, path: Path) -> list:
                # Both calls fail
                if str(path).endswith(".mp3"):
                    msg = (
                        "Audio file sample mismatch error. This usually indicates:\n"
                        "  - MP3 encoding imprecision (metadata doesn't match exact sample count)\n"
                        "Expected 10.00s (441000 samples), but got 9.97s (439895 samples)."
                    )
                    raise ValueError(msg)
                # WAV also fails
                msg = "WAV processing also failed"
                raise RuntimeError(msg)

            def mock_convert(_self: object, _input_path: Path, output_path: Path) -> None:
                output_path.write_bytes(b"fake_wav_data")

            with (
                patch.object(SpeakerDiarizer, "_diarize_audio_internal", mock_internal),
                patch.object(SpeakerDiarizer, "_convert_to_wav", mock_convert),
                pytest.raises(RuntimeError, match="WAV processing also failed"),
            ):
                diarizer.diarize_audio(audio_path)

            # WAV should be cleaned up even on failure
            wav_path = audio_path.with_suffix(".wav")
            assert not wav_path.exists()

        finally:
            if audio_path.exists():
                audio_path.unlink()

    def test_non_mp3_error_bypasses_conversion(self) -> None:
        """Test that errors without MP3 encoding text don't trigger conversion."""
        from vtt_transcribe.diarization import SpeakerDiarizer

        diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".mp3", delete=False) as f:
            audio_path = Path(f.name)
            f.write(b"fake_data")

        try:

            def mock_internal(_self: object, _path: Path) -> list:
                msg = "Some other error unrelated to MP3"
                raise ValueError(msg)

            with (
                patch.object(SpeakerDiarizer, "_diarize_audio_internal", mock_internal),
                pytest.raises(ValueError, match="Some other error unrelated to MP3"),
            ):
                diarizer.diarize_audio(audio_path)

        finally:
            if audio_path.exists():
                audio_path.unlink()

    def test_convert_to_wav_success(self) -> None:
        """Test WAV conversion using ffmpeg."""
        from vtt_transcribe.diarization import SpeakerDiarizer

        diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

        with (
            tempfile.NamedTemporaryFile(mode="wb", suffix=".mp3", delete=False) as f1,
            tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f2,
        ):
            input_path = Path(f1.name)
            output_path = Path(f2.name)
            f1.write(b"fake_mp3")

        try:
            # Mock subprocess to succeed
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            with patch("subprocess.run", return_value=mock_result):
                diarizer._convert_to_wav(input_path, output_path)

        finally:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_convert_to_wav_failure(self) -> None:
        """Test WAV conversion failure handling."""
        from vtt_transcribe.diarization import SpeakerDiarizer

        diarizer = SpeakerDiarizer(hf_token="test_token")  # noqa: S106

        with (
            tempfile.NamedTemporaryFile(mode="wb", suffix=".mp3", delete=False) as f1,
            tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f2,
        ):
            input_path = Path(f1.name)
            output_path = Path(f2.name)

        try:
            # Mock subprocess to fail
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "ffmpeg error: invalid file"

            with (
                patch("subprocess.run", return_value=mock_result),
                pytest.raises(RuntimeError, match="Failed to convert to WAV"),
            ):
                diarizer._convert_to_wav(input_path, output_path)

        finally:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()


class TestAudioPathResolution:
    """Test audio path resolution for diarization."""

    def test_audio_path_for_audio_input(self) -> None:
        """Test that audio input uses the input path directly."""
        from vtt_transcribe.handlers import handle_standard_transcription

        # Mock args with audio input
        args = Mock()
        args.input_file = "/path/to/audio.mp3"
        args.output_audio = None
        args.delete_audio = False
        args.force = False
        args.scan_chunks = False
        args.diarize = True
        args.hf_token = "test_token"  # noqa: S105
        args.device = "cpu"
        args.no_review_speakers = True

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "test transcript"

        mock_diarizer = MagicMock()
        mock_diarizer.diarize_audio.return_value = []
        mock_diarizer.apply_speakers_to_transcript.return_value = "test transcript with speakers"

        with (
            patch("vtt_transcribe.transcriber.VideoTranscriber", return_value=mock_transcriber) as mock_vt,
            patch("vtt_transcribe.handlers._lazy_import_diarization") as mock_lazy,
        ):
            # Set SUPPORTED_AUDIO_FORMATS on mock class
            mock_vt.SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav"]
            mock_lazy.return_value = (MagicMock(return_value=mock_diarizer), None, None, None)

            handle_standard_transcription(args, "test_api_key")

            # Should use input path directly for audio
            mock_diarizer.diarize_audio.assert_called_once()
            called_path = mock_diarizer.diarize_audio.call_args[0][0]
            assert str(called_path) == "/path/to/audio.mp3"

    def test_audio_path_with_custom_output(self) -> None:
        """Test that custom output path is used for diarization."""
        from vtt_transcribe.handlers import handle_standard_transcription

        args = Mock()
        args.input_file = "/path/to/video.mp4"
        args.output_audio = "/custom/audio.mp3"
        args.delete_audio = False
        args.force = False
        args.scan_chunks = False
        args.diarize = True
        args.hf_token = "test_token"  # noqa: S105
        args.device = "cpu"
        args.no_review_speakers = True

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "test transcript"

        mock_diarizer = MagicMock()
        mock_diarizer.diarize_audio.return_value = []
        mock_diarizer.apply_speakers_to_transcript.return_value = "test transcript with speakers"

        with (
            patch("vtt_transcribe.transcriber.VideoTranscriber", return_value=mock_transcriber) as mock_vt,
            patch("vtt_transcribe.handlers._lazy_import_diarization") as mock_lazy,
        ):
            # Set SUPPORTED_AUDIO_FORMATS on mock class
            mock_vt.SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav"]
            mock_lazy.return_value = (MagicMock(return_value=mock_diarizer), None, None, None)

            handle_standard_transcription(args, "test_api_key")

            # Should use custom output path
            mock_diarizer.diarize_audio.assert_called_once()
            called_path = mock_diarizer.diarize_audio.call_args[0][0]
            assert str(called_path) == "/custom/audio.mp3"

    def test_audio_path_default_from_video(self) -> None:
        """Test that default audio path is derived from video name."""
        from vtt_transcribe.handlers import handle_standard_transcription

        args = Mock()
        args.input_file = "/path/to/video.mp4"
        args.output_audio = None
        args.delete_audio = False
        args.force = False
        args.scan_chunks = False
        args.diarize = True
        args.hf_token = "test_token"  # noqa: S105
        args.device = "cpu"
        args.no_review_speakers = True

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "test transcript"

        mock_diarizer = MagicMock()
        mock_diarizer.diarize_audio.return_value = []
        mock_diarizer.apply_speakers_to_transcript.return_value = "test transcript with speakers"

        with (
            patch("vtt_transcribe.transcriber.VideoTranscriber", return_value=mock_transcriber) as mock_vt,
            patch("vtt_transcribe.handlers._lazy_import_diarization") as mock_lazy,
        ):
            # Set SUPPORTED_AUDIO_FORMATS on mock class
            mock_vt.SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav"]
            mock_lazy.return_value = (MagicMock(return_value=mock_diarizer), None, None, None)

            handle_standard_transcription(args, "test_api_key")

            # Should use video path with .mp3 extension
            mock_diarizer.diarize_audio.assert_called_once()
            called_path = mock_diarizer.diarize_audio.call_args[0][0]
            assert str(called_path) == "/path/to/video.mp3"


class TestStdinTempFileCreation:
    """Test stdin temp file creation with format detection."""

    def test_create_temp_file_with_filename_arg(self) -> None:
        """Test that filename argument overrides format detection."""
        from vtt_transcribe.main import _create_temp_file_from_stdin

        args = Mock()
        args.input_file = "video.mp4"

        mp4_data = b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 100

        with patch("sys.stdin.buffer.read", return_value=mp4_data):
            temp_path = _create_temp_file_from_stdin(args)

            try:
                assert temp_path.suffix == ".mp4"
                assert temp_path.exists()
                assert temp_path.read_bytes() == mp4_data
            finally:
                if temp_path.exists():
                    temp_path.unlink()

    def test_create_temp_file_without_filename_arg(self) -> None:
        """Test format detection when no filename argument provided."""
        from vtt_transcribe.main import _create_temp_file_from_stdin

        args = Mock()
        args.input_file = None

        mp4_data = b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 100

        with patch("sys.stdin.buffer.read", return_value=mp4_data):
            temp_path = _create_temp_file_from_stdin(args)

            try:
                assert temp_path.suffix == ".mp4"
                assert temp_path.exists()
                assert temp_path.read_bytes() == mp4_data
            finally:
                if temp_path.exists():
                    temp_path.unlink()

    def test_create_temp_file_webm_detection(self) -> None:
        """Test WebM format detection in stdin mode."""
        from vtt_transcribe.main import _create_temp_file_from_stdin

        args = Mock()
        args.input_file = None

        webm_data = b"\x1a\x45\xdf\xa3" + b"\x00" * 100

        with patch("sys.stdin.buffer.read", return_value=webm_data):
            temp_path = _create_temp_file_from_stdin(args)

            try:
                assert temp_path.suffix == ".webm"
                assert temp_path.exists()
            finally:
                if temp_path.exists():
                    temp_path.unlink()
