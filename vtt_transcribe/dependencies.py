"""System dependency checks for vtt-transcribe.

This module validates that required external dependencies (ffmpeg, torch, pyannote)
are installed before executing transcription workflows.
"""

import os
import shutil
import sys
from importlib.util import find_spec


def check_ffmpeg_installed() -> None:
    """Check if ffmpeg is installed and available in PATH.

    Exits with detailed installation instructions if ffmpeg is not found.
    """
    if shutil.which("ffmpeg") is None:
        print("\nError: ffmpeg is not installed or not in PATH.", file=sys.stderr)
        print(
            "\nffmpeg is required for audio extraction and processing.",
            file=sys.stderr,
        )
        print("\nInstallation instructions:", file=sys.stderr)
        print("  • Ubuntu/Debian: sudo apt-get install ffmpeg", file=sys.stderr)
        print("  • macOS (Homebrew): brew install ffmpeg", file=sys.stderr)
        print("  • Windows (Chocolatey): choco install ffmpeg", file=sys.stderr)
        print("  • Windows (Scoop): scoop install ffmpeg", file=sys.stderr)
        print("  • Or download from: https://ffmpeg.org/download.html\n", file=sys.stderr)
        sys.exit(1)


SHERPA_PACKAGES = ("sherpa_onnx", "numpy")
PYANNOTE_PACKAGES = ("pyannote.audio", "torch", "torchaudio")


def _missing(packages: tuple[str, ...]) -> list[str]:
    """Names from ``packages`` that cannot be found (without importing them)."""
    missing = []
    for pkg in packages:
        try:
            if find_spec(pkg) is None:
                missing.append(pkg)
        except (ModuleNotFoundError, ValueError):
            missing.append(pkg)
    return missing


def resolve_diarizer(choice: str = "auto") -> str:
    """Turn ``--diarizer`` into a concrete backend: "sherpa" or "pyannote".

    "auto" prefers sherpa when it is installed (no token, no torch) and otherwise falls back to
    pyannote, so existing pyannote-only installs keep working.
    """
    if choice != "auto":
        return choice
    return "sherpa" if not _missing(SHERPA_PACKAGES) else "pyannote"


def check_diarization_dependencies(diarizer: str = "auto") -> None:
    """Check that the dependencies for the chosen diarization backend are installed.

    Uses importlib to check package availability without triggering heavy
    native library loading (torchcodec C++ extensions can crash on systems
    without proper FFmpeg/codec libraries).

    Exits with installation instructions if dependencies are not found.
    """
    sherpa_missing = _missing(SHERPA_PACKAGES)
    pyannote_missing = _missing(PYANNOTE_PACKAGES)

    if diarizer == "sherpa":
        missing, hint = sherpa_missing, "pip install vtt-transcribe[sherpa]"
    elif diarizer == "pyannote":
        missing, hint = pyannote_missing, "pip install vtt-transcribe[diarization]"
    else:  # auto: either backend is enough
        missing = [] if not sherpa_missing or not pyannote_missing else sherpa_missing
        hint = "pip install vtt-transcribe[sherpa] or: pip install vtt-transcribe[diarization] (pyannote backend)"

    if missing:
        print("\nError: Diarization dependencies not installed.", file=sys.stderr)
        print(f"  Missing: {', '.join(missing)}", file=sys.stderr)
        print(f"Install with: {hint}\n", file=sys.stderr)
        sys.exit(1)


def check_local_dependencies() -> None:
    """Exit with install instructions when the local engine's faster-whisper is missing."""
    if not local_available():
        print("\nError: the local engine needs faster-whisper.", file=sys.stderr)
        print("Install with: pip install vtt-transcribe[local]\n", file=sys.stderr)
        sys.exit(1)


def local_available() -> bool:
    """True when faster-whisper is installed (checked without importing it)."""
    return not _missing(("faster_whisper",))


def resolve_engine(choice: str, api_key: str | None) -> str:
    """Turn ``--engine`` into "openai" or "local". "auto" picks local when installed and no key is set."""
    if choice != "auto":
        return choice
    return "local" if local_available() and not (api_key or os.environ.get("OPENAI_API_KEY")) else "openai"
