import nox

# Default sessions
nox.options.sessions = ["tests", "tests_core", "lint"]


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
def tests(session: nox.Session) -> None:
    """Run the test suite with diarization support (Python 3.10-3.13).

    Installs the package in editable mode with dev and diarization extras and runs pytest.
    Diarization extras (torch) have prebuilt wheels only up to Python 3.13.
    """
    session.install("pip>=23.0")
    # Install package and all extras in a single resolver pass.
    # The PyTorch CPU wheel index is added as an extra source so that
    # torch==2.8.0 and torchaudio==2.8.0 resolve to their +cpu variants
    # (which don't require libcudart) instead of the CUDA builds on PyPI.
    # torchaudio is pinned to 2.8.0 (matching torch) to prevent pip from
    # upgrading to a newer CUDA torchaudio from PyPI which would produce an
    # ABI mismatch ("undefined symbol: torch_library_impl").
    session.install(
        "--extra-index-url",
        "https://download.pytorch.org/whl/cpu",
        ".[dev,api,diarization]",
        "torch==2.8.0",
        "torchaudio==2.8.0",
    )
    session.env.update(
        {
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_CLIENT_SECRET": "",
            "GITHUB_CLIENT_ID": "",
            "GITHUB_CLIENT_SECRET": "",
            "FRONTEND_URL": "http://localhost:3000",
        }
    )
    # Run tests
    session.run("pytest", "-q")


@nox.session(python=["3.14"])
def tests_core(session: nox.Session) -> None:
    """Run core tests only for Python 3.14 (without diarization).

    Python 3.14 does not have prebuilt torch wheels yet, so we test only
    the core functionality without diarization extras. Tests marked with
    @pytest.mark.diarization are skipped.
    """
    session.install("pip>=23.0")
    # Install package with development and API extras (no diarization)
    session.install(".[dev,api]")
    session.env.update(
        {
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_CLIENT_SECRET": "",
            "GITHUB_CLIENT_ID": "",
            "GITHUB_CLIENT_SECRET": "",
            "FRONTEND_URL": "http://localhost:3000",
        }
    )
    # Run tests, skipping those that require diarization dependencies
    session.run("pytest", "-q", "-m", "not diarization")


@nox.session(python=["3.10"])
def lint(session: nox.Session) -> None:
    """Run linters/formatters (ruff, mypy) on Python 3.10."""
    session.install("pip>=23.0")
    session.install(".[dev,api]")
    # Run ruff
    session.run("ruff", "check", ".")
    # Run mypy with strict type checking
    session.run(
        "mypy",
        "vtt_transcribe",
        "--ignore-missing-imports",
        "--disallow-untyped-defs",
        "--disallow-incomplete-defs",
        "--check-untyped-defs",
        "--warn-unused-ignores",
        "--warn-redundant-casts",
    )
