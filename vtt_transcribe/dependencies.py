"""System dependency checks for vtt-transcribe.

This module validates that required external dependencies (ffmpeg, torch, pyannote)
are installed before executing transcription workflows.
"""

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


def check_diarization_dependencies() -> None:
    """Check if diarization dependencies (torch, pyannote) are installed.

    Uses importlib to check package availability without triggering heavy
    native library loading (torchcodec C++ extensions can crash on systems
    without proper FFmpeg/codec libraries).

    Exits with installation instructions if dependencies are not found.
    """
    missing = []
    for pkg in ("pyannote.audio", "torch", "torchaudio"):
        try:
            if find_spec(pkg) is None:
                missing.append(pkg)
        except (ModuleNotFoundError, ValueError):
            missing.append(pkg)

    if missing:
        print("\nError: Diarization dependencies not installed.", file=sys.stderr)
        print(f"  Missing: {', '.join(missing)}", file=sys.stderr)
        print(
            "Install with: pip install vtt-transcribe[diarization] or: uv pip install vtt-transcribe[diarization]\n",
            file=sys.stderr,
        )
        sys.exit(1)
