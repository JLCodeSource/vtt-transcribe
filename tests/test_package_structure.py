"""Tests for package structure and entry points."""

import subprocess
import sys
from importlib.metadata import metadata

from packaging.requirements import Requirement


def test_diarization_extra_pins_pyannote_below_4() -> None:
    """Test that pyannote.audio is pinned to <4.0.0 in diarization extra.

    pyannote.audio 4.x switched audio I/O from torchaudio to torchcodec,
    which requires torch>=2.10 and is incompatible with our torch==2.8.0 pin.
    This causes 'NameError: name AudioDecoder is not defined' at runtime.
    See: https://github.com/pyannote/pyannote-audio/blob/main/CHANGELOG.md#version-400
    """
    meta = metadata("vtt-transcribe")
    # Get all optional dependencies (extras)
    requires = meta.get_all("Requires-Dist") or []

    # Find pyannote.audio requirement in diarization extra
    pyannote_reqs = [Requirement(r) for r in requires if "pyannote" in r and "diarization" in r]
    assert len(pyannote_reqs) == 1, f"Expected exactly 1 pyannote.audio req in diarization extra, got: {pyannote_reqs}"

    req = pyannote_reqs[0]
    # Verify that version 4.0.0 is NOT allowed by the specifier
    assert not req.specifier.contains("4.0.0"), (
        f"pyannote.audio specifier {req.specifier} allows version 4.0.0, "
        "which is incompatible with torch==2.8.0 (torchcodec ABI mismatch)"
    )
    # Verify that version 3.3.2 IS allowed
    assert req.specifier.contains("3.3.2"), f"pyannote.audio specifier {req.specifier} should allow 3.x versions"


def test_diarization_extra_requires_torchaudio() -> None:
    """Test that torchaudio is required in diarization extra.

    pyannote.audio 3.x uses torchaudio for audio I/O. Without torchaudio,
    'import pyannote.audio' fails with ImportError, causing the
    'Diarization dependencies not installed' error message.
    """
    meta = metadata("vtt-transcribe")
    requires = meta.get_all("Requires-Dist") or []

    torchaudio_reqs = [Requirement(r) for r in requires if "torchaudio" in r and "diarization" in r]
    assert len(torchaudio_reqs) == 1, f"Expected torchaudio in diarization extra, got: {torchaudio_reqs}"

    req = torchaudio_reqs[0]
    # Verify that torchaudio 2.2.0+ is allowed (matching pyannote.audio 3.x requirement)
    assert req.specifier.contains("2.2.0"), f"torchaudio specifier {req.specifier} should allow 2.2.0"
    assert req.specifier.contains("2.8.0"), f"torchaudio specifier {req.specifier} should allow 2.8.0"


def test_vtt_transcribe_package_import() -> None:
    """Test that vtt_transcribe package can be imported."""
    import vtt_transcribe

    assert vtt_transcribe is not None
    assert hasattr(vtt_transcribe, "__version__")
    version = vtt_transcribe.__version__
    assert isinstance(version, str)
    assert version != ""


def test_vtt_cli_entry_point_exists() -> None:
    """Test that vtt CLI command is available."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "vtt_transcribe.main", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert "usage: vtt" in result.stdout or "Transcribe" in result.stdout


def test_vtt_command_via_entry_point() -> None:
    """Test that 'vtt' command exists as entry point."""
    # This tests the entry point defined in pyproject.toml
    import_code = (
        "from importlib.metadata import entry_points; "
        "eps = entry_points(); "
        "print([ep for ep in eps.select(group='console_scripts') if ep.name == 'vtt'])"
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", import_code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert "vtt" in result.stdout
