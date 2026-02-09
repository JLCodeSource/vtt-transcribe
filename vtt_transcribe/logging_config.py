"""Logging configuration module for vtt-transcribe.

This module provides structured logging with environment-based configuration,
supporting both human-readable dev logs and JSON-formatted production logs.
"""

import logging
import os
import sys


def get_environment() -> str:
    """Get the current environment from VTT_ENV variable.

    Returns:
        Environment name ("production" or "development")
    """
    return os.getenv("VTT_ENV", "development")


def is_production() -> bool:
    """Check if running in production environment.

    Returns:
        True if VTT_ENV is set to "production", False otherwise
    """
    return get_environment() == "production"


def setup_logging(*, dev_mode: bool | None = None) -> logging.Logger:
    """Set up and configure logging for vtt-transcribe.

    Args:
        dev_mode: If True, use DEBUG level and human-readable format.
                 If False, use INFO level and JSON format.
                 If None, auto-detect from environment.

    Returns:
        Configured logger instance
    """
    # Auto-detect environment if not specified
    if dev_mode is None:
        dev_mode = not is_production()

    # Create or get logger
    logger = logging.getLogger("vtt_transcribe")

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set log level based on mode
    logger.setLevel(logging.DEBUG if dev_mode else logging.INFO)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if dev_mode else logging.INFO)

    # Configure formatter based on environment
    if dev_mode:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # JSON format for production (simplified for now)
        # We'll enhance this with proper JSON formatting in refactor phase
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    # Return child logger of main vtt_transcribe logger
    return logging.getLogger(f"vtt_transcribe.{name}")
