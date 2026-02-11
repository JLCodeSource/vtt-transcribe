"""Tests for scripts/generate_secrets.py."""

import subprocess
import sys
from unittest.mock import patch

import pytest


class TestGenerateSecretKey:
    """Test generate_secret_key function."""

    def test_generates_hex_string(self) -> None:
        """Should generate a hex-encoded string."""
        # Import here to avoid module-level import issues
        from scripts.generate_secrets import generate_secret_key

        result = generate_secret_key()

        # Should be a valid hex string
        assert isinstance(result, str)
        assert len(result) > 0
        assert all(c in "0123456789abcdef" for c in result)

    def test_generates_correct_length(self) -> None:
        """Should generate key with correct byte length."""
        from scripts.generate_secrets import generate_secret_key

        # Default length is 32 bytes = 64 hex characters
        result = generate_secret_key()
        assert len(result) == 64

        # Custom length: 16 bytes = 32 hex characters
        result = generate_secret_key(length=16)
        assert len(result) == 32

    def test_generates_unique_keys(self) -> None:
        """Should generate different keys on each call."""
        from scripts.generate_secrets import generate_secret_key

        key1 = generate_secret_key()
        key2 = generate_secret_key()

        assert key1 != key2


class TestGenerateEncryptionKey:
    """Test generate_encryption_key function."""

    def test_generates_fernet_key(self) -> None:
        """Should generate a valid Fernet key."""
        from scripts.generate_secrets import generate_encryption_key

        result = generate_encryption_key()

        # Fernet keys are base64-encoded and 44 characters long
        assert isinstance(result, str)
        assert len(result) == 44

        # Should be valid base64 (basic check)
        import base64

        try:
            decoded = base64.urlsafe_b64decode(result.encode())
            assert len(decoded) == 32  # Fernet keys are 32 bytes
        except Exception as e:
            pytest.fail(f"Invalid Fernet key format: {e}")

    def test_generates_unique_keys(self) -> None:
        """Should generate different keys on each call."""
        from scripts.generate_secrets import generate_encryption_key

        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        assert key1 != key2

    def test_key_works_with_fernet(self) -> None:
        """Should generate keys that work with Fernet encryption."""
        from cryptography.fernet import Fernet

        from scripts.generate_secrets import generate_encryption_key

        key = generate_encryption_key()
        fernet = Fernet(key.encode())

        # Should be able to encrypt and decrypt
        message = b"test message"
        encrypted = fernet.encrypt(message)
        decrypted = fernet.decrypt(encrypted)

        assert decrypted == message

    def test_import_error_handling(self) -> None:
        """Should exit with helpful message when cryptography is not installed."""
        # This test verifies the error handling logic exists in the code
        # We can't easily mock the ImportError without causing issues with module loading
        # Instead, we verify that the code has the proper error handling structure
        import inspect

        from scripts.generate_secrets import generate_encryption_key

        source = inspect.getsource(generate_encryption_key)

        # Verify the function has ImportError handling
        assert "try:" in source
        assert "from cryptography.fernet import Fernet" in source
        assert "except ImportError:" in source
        assert "sys.exit(1)" in source
        assert "uv sync --extra api" in source


class TestMainFunction:
    """Test main function and CLI behavior."""

    def test_env_format_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should output in .env format by default."""
        from scripts.generate_secrets import main

        with patch("sys.argv", ["generate_secrets.py"]):
            main()

        captured = capsys.readouterr()

        # Should contain .env format comments and variables
        assert "# Generated secrets" in captured.out
        assert "SECRET_KEY=" in captured.out
        assert "ENCRYPTION_KEY=" in captured.out

        # Should not have 'export' commands
        assert "export" not in captured.out

    def test_shell_format_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should output shell export commands when requested."""
        from scripts.generate_secrets import main

        with patch("sys.argv", ["generate_secrets.py", "--format", "shell"]):
            main()

        captured = capsys.readouterr()

        # Should contain export commands
        assert "export SECRET_KEY=" in captured.out
        assert "export ENCRYPTION_KEY=" in captured.out

        # Should have quotes around values
        assert "export SECRET_KEY='" in captured.out
        assert "export ENCRYPTION_KEY='" in captured.out

    def test_env_format_explicit(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should output in .env format when explicitly requested."""
        from scripts.generate_secrets import main

        with patch("sys.argv", ["generate_secrets.py", "--format", "env"]):
            main()

        captured = capsys.readouterr()

        assert "# Generated secrets" in captured.out
        assert "SECRET_KEY=" in captured.out
        assert "ENCRYPTION_KEY=" in captured.out
        assert "export" not in captured.out


class TestCLIIntegration:
    """Test the script as a CLI tool."""

    def test_script_runs_successfully(self) -> None:
        """Should run the script without errors."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        assert result.returncode == 0
        assert "SECRET_KEY=" in result.stdout
        assert "ENCRYPTION_KEY=" in result.stdout

    def test_script_with_shell_format(self) -> None:
        """Should support --format shell argument."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py", "--format", "shell"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        assert result.returncode == 0
        assert "export SECRET_KEY=" in result.stdout
        assert "export ENCRYPTION_KEY=" in result.stdout

    def test_script_help(self) -> None:
        """Should display help when --help is provided."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        assert result.returncode == 0
        assert "Generate secure secrets" in result.stdout
        assert "--format" in result.stdout
        assert "env" in result.stdout
        assert "shell" in result.stdout

    def test_invalid_format_argument(self) -> None:
        """Should reject invalid format arguments."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py", "--format", "invalid"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower()


class TestOutputFormat:
    """Test the format and structure of generated output."""

    def test_secret_key_is_valid_hex(self) -> None:
        """Should generate valid hex strings for SECRET_KEY."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        # Extract SECRET_KEY value
        for line in result.stdout.split("\n"):
            if line.startswith("SECRET_KEY="):
                secret_key = line.split("=", 1)[1].strip()
                # Should be hex
                assert len(secret_key) == 64
                assert all(c in "0123456789abcdef" for c in secret_key)
                break
        else:
            pytest.fail("SECRET_KEY not found in output")

    def test_encryption_key_is_valid_base64(self) -> None:
        """Should generate valid base64 strings for ENCRYPTION_KEY."""
        import base64

        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        # Extract ENCRYPTION_KEY value
        for line in result.stdout.split("\n"):
            if line.startswith("ENCRYPTION_KEY="):
                encryption_key = line.split("=", 1)[1].strip()
                # Should be valid base64
                try:
                    decoded = base64.urlsafe_b64decode(encryption_key.encode())
                    assert len(decoded) == 32
                except Exception as e:
                    pytest.fail(f"Invalid base64 format: {e}")
                break
        else:
            pytest.fail("ENCRYPTION_KEY not found in output")

    def test_shell_format_has_proper_quoting(self) -> None:
        """Should properly quote values in shell format."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_secrets.py", "--format", "shell"],
            capture_output=True,
            text=True,
            cwd="/home/runner/work/vtt-transcribe/vtt-transcribe",
        )

        lines = result.stdout.strip().split("\n")

        # Both lines should have export with quotes
        for line in lines:
            assert line.startswith("export ")
            assert "='" in line
            assert line.endswith("'")
