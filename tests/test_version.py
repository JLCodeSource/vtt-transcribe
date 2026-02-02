"""Tests for version handling."""

import subprocess
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch


def test_version_when_package_installed() -> None:
    """Should retrieve version from package metadata when installed."""
    import vtt_transcribe

    # When installed normally, __version__ should be a valid version string
    assert vtt_transcribe.__version__ is not None
    assert isinstance(vtt_transcribe.__version__, str)


def test_version_when_package_not_found() -> None:
    """Should fall back to 'unknown' when package not found."""
    # Mock the version function to raise PackageNotFoundError
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        # Force re-import to trigger the except block
        import importlib

        import vtt_transcribe

        importlib.reload(vtt_transcribe)

        assert vtt_transcribe.__version__ == "unknown"


def test_version_flag_long() -> None:
    """Should display version with --version flag."""
    result = subprocess.run(["vtt", "--version"], capture_output=True, text=True, check=False)  # noqa: S607
    assert result.returncode == 0
    assert "vtt" in result.stdout
    # Check that version is displayed (format: "vtt X.Y.Z" or "vtt unknown")
    assert any(char.isdigit() or result.stdout.strip().endswith("unknown") for char in result.stdout)


def test_version_flag_short() -> None:
    """Should display version with -v flag."""
    result = subprocess.run(["vtt", "-v"], capture_output=True, text=True, check=False)  # noqa: S607
    assert result.returncode == 0
    assert "vtt" in result.stdout
    # Check that version is displayed (format: "vtt X.Y.Z" or "vtt unknown")
    assert any(char.isdigit() or result.stdout.strip().endswith("unknown") for char in result.stdout)
