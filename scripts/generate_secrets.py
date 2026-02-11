#!/usr/bin/env python3
"""Generate secure secrets for vtt-transcribe configuration.

This script generates cryptographically secure keys required for the application:
- SECRET_KEY: Used for JWT token signing
- ENCRYPTION_KEY: Used for API key encryption (Fernet format)

Usage:
    python scripts/generate_secrets.py [--format env|shell]

Examples:
    # Output in .env format (default)
    python scripts/generate_secrets.py

    # Output as shell export commands
    python scripts/generate_secrets.py --format shell

    # Append to .env file
    python scripts/generate_secrets.py >> .env
"""

import argparse
import secrets
import sys


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure random secret key.

    Args:
        length: Length of the secret key in bytes (default: 32)

    Returns:
        Hex-encoded secret key
    """
    return secrets.token_hex(length)


def generate_encryption_key() -> str:
    """Generate a Fernet encryption key.

    Returns:
        Base64-encoded Fernet key suitable for cryptography.fernet
    """
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print(
            "Error: 'cryptography' package is required to generate encryption keys.",
            file=sys.stderr,
        )
        print("\nInstall it with one of the following commands:", file=sys.stderr)
        print("  uv sync --extra api", file=sys.stderr)
        print("  make install-api", file=sys.stderr)
        print("  pip install cryptography", file=sys.stderr)
        sys.exit(1)
    
    return Fernet.generate_key().decode()


def main() -> None:
    """Generate and output secure secrets."""
    parser = argparse.ArgumentParser(
        description="Generate secure secrets for vtt-transcribe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--format",
        choices=["env", "shell"],
        default="env",
        help="Output format: 'env' for .env file format, 'shell' for export commands",
    )

    args = parser.parse_args()

    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()

    if args.format == "shell":
        print(f"export SECRET_KEY='{secret_key}'")
        print(f"export ENCRYPTION_KEY='{encryption_key}'")
    else:  # env format
        print("# Generated secrets - Add these to your .env file")
        print(f"SECRET_KEY={secret_key}")
        print(f"ENCRYPTION_KEY={encryption_key}")


if __name__ == "__main__":
    main()
