"""Tests for dependency checks in vtt_transcribe.dependencies module."""

from unittest.mock import Mock, patch

import pytest


def _mock_find_spec_missing_all(name: str):  # type: ignore[no-untyped-def]
    """Mock find_spec that reports all diarization packages as missing."""
    if name in ("pyannote.audio", "torch", "torchaudio"):
        return None
    return Mock()


def test_check_ffmpeg_installed_when_available() -> None:
    """Test check_ffmpeg_installed() passes when ffmpeg is available."""
    from vtt_transcribe.dependencies import check_ffmpeg_installed

    with patch("vtt_transcribe.dependencies.shutil.which", return_value="/usr/bin/ffmpeg"):
        # Should not raise or exit
        check_ffmpeg_installed()


def test_check_ffmpeg_installed_when_missing() -> None:
    """Test check_ffmpeg_installed() exits when ffmpeg is not found."""
    from vtt_transcribe.dependencies import check_ffmpeg_installed

    with (
        patch("vtt_transcribe.dependencies.shutil.which", return_value=None),
        pytest.raises(SystemExit) as exc_info,
    ):
        check_ffmpeg_installed()

    assert exc_info.value.code == 1


def test_check_ffmpeg_prints_error_message() -> None:
    """Test check_ffmpeg_installed() prints helpful error message."""
    from vtt_transcribe.dependencies import check_ffmpeg_installed

    with (
        patch("vtt_transcribe.dependencies.shutil.which", return_value=None),
        patch("builtins.print") as mock_print,
        pytest.raises(SystemExit),
    ):
        check_ffmpeg_installed()

    # Verify error message was printed
    print_calls = [str(call) for call in mock_print.call_args_list]
    error_output = " ".join(print_calls)
    assert "ffmpeg is not installed" in error_output
    assert "Installation instructions" in error_output


def test_check_diarization_dependencies_when_available() -> None:
    """Test check_diarization_dependencies() passes when dependencies are available."""
    from vtt_transcribe.dependencies import check_diarization_dependencies

    # Mock find_spec to report all packages as found
    with patch("vtt_transcribe.dependencies.find_spec", return_value=Mock()):
        # Should not raise or exit
        check_diarization_dependencies()


def test_check_diarization_dependencies_when_missing() -> None:
    """Test check_diarization_dependencies() exits when dependencies are not found."""
    from vtt_transcribe.dependencies import check_diarization_dependencies

    with (
        patch("vtt_transcribe.dependencies.find_spec", side_effect=_mock_find_spec_missing_all),
        pytest.raises(SystemExit) as exc_info,
    ):
        check_diarization_dependencies()

    assert exc_info.value.code == 1


def test_check_diarization_dependencies_prints_error_message() -> None:
    """Test check_diarization_dependencies() prints helpful error message."""
    from vtt_transcribe.dependencies import check_diarization_dependencies

    with (
        patch("vtt_transcribe.dependencies.find_spec", side_effect=_mock_find_spec_missing_all),
        patch("builtins.print") as mock_print,
        pytest.raises(SystemExit),
    ):
        check_diarization_dependencies()

    # Verify error message was printed
    print_calls = [str(call) for call in mock_print.call_args_list]
    error_output = " ".join(print_calls)
    assert "Diarization dependencies not installed" in error_output
    assert "pip install vtt-transcribe[diarization]" in error_output
    assert "Missing:" in error_output


def test_check_diarization_dependencies_handles_torch_missing() -> None:
    """Test that missing torch is caught."""
    from vtt_transcribe.dependencies import check_diarization_dependencies

    def find_spec_no_torch(name: str):  # type: ignore[no-untyped-def]
        if name == "torch":
            return None
        return Mock()

    with (
        patch("vtt_transcribe.dependencies.find_spec", side_effect=find_spec_no_torch),
        pytest.raises(SystemExit) as exc_info,
    ):
        check_diarization_dependencies()
    assert exc_info.value.code == 1


def test_check_diarization_dependencies_handles_pyannote_missing() -> None:
    """Test that missing pyannote.audio is caught."""
    from vtt_transcribe.dependencies import check_diarization_dependencies

    def find_spec_no_pyannote(name: str):  # type: ignore[no-untyped-def]
        if name == "pyannote.audio":
            return None
        return Mock()

    with (
        patch("vtt_transcribe.dependencies.find_spec", side_effect=find_spec_no_pyannote),
        pytest.raises(SystemExit) as exc_info,
    ):
        check_diarization_dependencies()
    assert exc_info.value.code == 1


def test_check_diarization_dependencies_handles_torchaudio_missing() -> None:
    """Test that missing torchaudio is caught."""
    from vtt_transcribe.dependencies import check_diarization_dependencies

    def find_spec_no_torchaudio(name: str):  # type: ignore[no-untyped-def]
        if name == "torchaudio":
            return None
        return Mock()

    with (
        patch("vtt_transcribe.dependencies.find_spec", side_effect=find_spec_no_torchaudio),
        pytest.raises(SystemExit) as exc_info,
    ):
        check_diarization_dependencies()
    assert exc_info.value.code == 1


class TestDependenciesCoverage:
    """Tests to cover missing lines in dependencies.py."""

    def test_check_diarization_dependencies_with_module_not_found_exception(self) -> None:
        """Test diarization dependency check handles ModuleNotFoundError in find_spec (lines 46-47)."""

        with (
            patch("vtt_transcribe.dependencies.find_spec") as mock_find,
            patch("sys.stderr"),
            pytest.raises(SystemExit) as exc_info,
        ):
            # Simulate ModuleNotFoundError during find_spec
            mock_find.side_effect = ModuleNotFoundError("No module named 'torch'")

            from vtt_transcribe.dependencies import check_diarization_dependencies

            check_diarization_dependencies()

        assert exc_info.value.code == 1

    def test_check_diarization_dependencies_with_value_error(self) -> None:
        """Test diarization dependency check handles ValueError in find_spec (lines 46-47)."""
        with (
            patch("vtt_transcribe.dependencies.find_spec") as mock_find,
            patch("sys.stderr"),
            pytest.raises(SystemExit) as exc_info,
        ):
            # Simulate ValueError during find_spec (can happen with malformed module names)
            mock_find.side_effect = ValueError("Invalid module spec")

            from vtt_transcribe.dependencies import check_diarization_dependencies

            check_diarization_dependencies()

        assert exc_info.value.code == 1
