"""Pytest configuration for loading environment variables."""

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Set required environment variables for API tests BEFORE any imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-only")
os.environ.setdefault("ENCRYPTION_KEY", "eZG7WcaEfouAvUvzsF8dpS1Arw-lfhjCs5LU4gzuXVE=")

# Load .env file at module import time (before pytest collection)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)  # Don't override test values


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Ensure environment variables are loaded from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)  # Don't override test values


@pytest.fixture(autouse=True)
def mock_stdin_tty() -> Generator[MagicMock]:
    """Mock sys.stdin.isatty() to return True by default for all tests.

    This prevents stdin mode from activating unexpectedly in test environments.
    Tests that specifically want to test stdin mode should override this by
    patching sys.stdin with their own mock.
    """
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        yield mock_stdin


@pytest.fixture(scope="session")
def gpu_available() -> bool:
    """Check if GPU (CUDA) is available for testing.

    Returns:
        bool: True if CUDA GPU is available, False otherwise.
    """
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False
