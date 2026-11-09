"""Tests for package structure and entry points."""

import subprocess
import sys
from importlib.metadata import metadata

from packaging.requirements import Requirement


def test_diarization_extra_requires_pyannote_4x() -> None:
    """Test that pyannote.audio >=4.0.0 is required in diarization extra.

    pyannote.audio 4.x uses torchcodec for audio decoding (actively maintained).
    Combined with torchcodec<0.8 pin for torch 2.8.0 ABI compatibility.
    """
    meta = metadata("vtt-transcribe")
    # Get all optional dependencies (extras)
    requires = meta.get_all("Requires-Dist") or []

    # Find pyannote.audio requirement in diarization extra
    pyannote_reqs = [Requirement(r) for r in requires if "pyannote" in r and "diarization" in r]
    assert len(pyannote_reqs) == 1, f"Expected exactly 1 pyannote.audio req in diarization extra, got: {pyannote_reqs}"

    req = pyannote_reqs[0]
    # Verify that version 4.0.4 IS allowed
    assert req.specifier.contains("4.0.4"), f"pyannote.audio specifier {req.specifier} should allow 4.0.4"
    # Verify that version 3.x is NOT allowed (we require >=4.0.0)
    assert not req.specifier.contains("3.4.0"), (
        f"pyannote.audio specifier {req.specifier} allows version 3.4.0, but we require >=4.0.0 for torchcodec-based audio I/O"
    )


def test_diarization_extra_requires_torchaudio() -> None:
    """Test that torchaudio is required in diarization extra.

    pyannote.audio 4.x uses torchaudio for audio resampling.
    """
    meta = metadata("vtt-transcribe")
    requires = meta.get_all("Requires-Dist") or []

    torchaudio_reqs = [Requirement(r) for r in requires if "torchaudio" in r and "diarization" in r]
    assert len(torchaudio_reqs) == 1, f"Expected torchaudio in diarization extra, got: {torchaudio_reqs}"

    req = torchaudio_reqs[0]
    # torchaudio 2.11.1 is its last release; it is pinned to match the torch 2.15 ABI-tested pairing.
    assert req.specifier.contains("2.11.1"), f"torchaudio specifier {req.specifier} should allow 2.11.1"


def test_diarization_extra_requires_torchcodec() -> None:
    """Test that torchcodec is pinned to a release that loads against torch 2.15.

    pyannote.audio 4.x uses torchcodec for audio decoding. torchcodec 0.14+ fails to
    load against torch 2.15 (libtorchcodec ABI), so the pin must not allow it.
    """
    meta = metadata("vtt-transcribe")
    requires = meta.get_all("Requires-Dist") or []

    torchcodec_reqs = [Requirement(r) for r in requires if "torchcodec" in r and "diarization" in r]
    assert len(torchcodec_reqs) == 1, f"Expected torchcodec in diarization extra, got: {torchcodec_reqs}"

    req = torchcodec_reqs[0]
    assert req.specifier.contains("0.13.0"), f"torchcodec specifier {req.specifier} should allow 0.13.0"
    assert not req.specifier.contains("0.14.0"), (
        f"torchcodec specifier {req.specifier} allows 0.14.0, which fails to load against torch 2.15"
    )


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
    result = subprocess.run(
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
    result = subprocess.run(
        [sys.executable, "-c", import_code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert "vtt" in result.stdout
