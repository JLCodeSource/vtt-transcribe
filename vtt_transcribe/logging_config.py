"""Logging configuration module for vtt-transcribe.

This module provides structured logging with environment-based configuration,
supporting both human-readable dev logs and JSON-formatted production logs.
"""

import json
import logging
import os
import sys
from typing import Any


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
        # Proper JSON format for production
        formatter = JsonFormatter()

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
    # If the name is already under the vtt_transcribe namespace, use it as-is;
    # otherwise, create a child logger of the main vtt_transcribe logger.
    if name == "vtt_transcribe" or name.startswith("vtt_transcribe."):
        return logging.getLogger(name)
    return logging.getLogger(f"vtt_transcribe.{name}")


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        # Preserve custom fields passed via extra={} in log calls
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "msecs",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "processName",
                "process",
                "threadName",
                "thread",
                "taskName",
                "relativeCreated",
            ):
                log_data[key] = value

        return json.dumps(log_data)
