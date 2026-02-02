"""Tests for version handling."""

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
