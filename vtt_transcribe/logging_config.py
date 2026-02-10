"""Logging configuration module for vtt-transcribe.

This module provides structured logging with environment-based configuration,
supporting both human-readable dev logs and JSON-formatted production logs.
"""

import json
import logging
import logging.handlers
import os
import sys
import uuid
from collections.abc import Generator, MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Context variables for tracking operations across async boundaries
_context_data: ContextVar[dict[str, Any] | None] = ContextVar("context_data", default=None)


@contextmanager
def operation_context(operation_name: str, *, operation_id: str | None = None, **context: Any) -> Generator[str, None, None]:
    """Context manager for tracking operations with correlation IDs.

    This provides request/operation tracking across module boundaries.
    The operation_id and context data are automatically included in all
    log messages within the context.

    Args:
        operation_name: Name of the operation being tracked
        operation_id: Optional correlation ID (generates one if not provided)
        **context: Additional context data to include in logs

    Yields:
        The operation ID for this context

    Example:
        with operation_context("transcribe_audio", filename="test.mp3") as op_id:
            logger.info("Starting transcription")  # Includes op_id and filename
    """
    # Generate operation ID if not provided
    if operation_id is None:
        operation_id = str(uuid.uuid4())

    # Prevent overriding reserved keys via **context
    reserved_keys = {"operation_id", "operation_name"}
    overridden_keys = reserved_keys.intersection(context.keys())
    if overridden_keys:
        msg = f"Reserved context key(s) cannot be overridden: {', '.join(sorted(overridden_keys))}"
        raise ValueError(msg)

    # Merge context data - reserved keys are set last to prevent override
    current_context = _context_data.get() or {}
    merged_context = {
        **current_context,
        **context,
        "operation_name": operation_name,
        "operation_id": operation_id,
    }

    # Set context variable
    token_context = _context_data.set(merged_context)

    try:
        yield operation_id
    finally:
        _context_data.reset(token_context)


def get_operation_context() -> dict[str, Any]:
    """Get the current operation context data.

    Returns:
        Dictionary with current operation context, empty if no context set
    """
    context = _context_data.get()
    return context.copy() if context is not None else {}


if TYPE_CHECKING:
    # For type checking only - Python 3.10 doesn't support subscripting at runtime
    _LoggerAdapterBase = logging.LoggerAdapter[logging.Logger]
else:
    _LoggerAdapterBase = logging.LoggerAdapter


class ContextualLoggerAdapter(_LoggerAdapterBase):
    """Logger adapter that automatically includes operation context in log records."""

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        """Process log record to include operation context.

        Args:
            msg: Log message
            kwargs: Log kwargs including 'extra'

        Returns:
            Tuple of (message, updated kwargs)
        """
        # Get current context
        context = get_operation_context()

        if context:
            # Merge context with any existing extra data
            extra = kwargs.get("extra", {})
            kwargs["extra"] = {**context, **extra}

        return msg, kwargs


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


def setup_logging(
    *,
    dev_mode: bool | None = None,
    use_stderr: bool = False,
    log_file: str | Path | None = None,
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up and configure logging for vtt-transcribe.

    Args:
        dev_mode: If True, use DEBUG level and human-readable format.
                 If False, use INFO level and JSON format.
                 If None, auto-detect from environment.
        use_stderr: If True, log to stderr instead of stdout.
                   Use this in stdin mode to avoid polluting stdout.
        log_file: Optional file path for file logging. If provided, logs
                 will be written to both console and file.
        enable_rotation: If True and log_file is set, enable log rotation.
        max_bytes: Maximum size of log file before rotation (default 10MB).
        backup_count: Number of rotated log files to keep (default 5).

    Returns:
        Configured logger instance
    """
    # Auto-detect environment if not specified
    if dev_mode is None:
        dev_mode = not is_production()

    # Create or get logger
    logger = logging.getLogger("vtt_transcribe")

    # Close and remove existing handlers to avoid duplicates and resource leaks
    for handler in logger.handlers[:]:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)

    # Set log level based on mode
    logger.setLevel(logging.DEBUG if dev_mode else logging.INFO)

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

    # Create console handler - use stderr in stdin mode to avoid polluting stdout
    stream = sys.stderr if use_stderr else sys.stdout
    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(logging.DEBUG if dev_mode else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if enable_rotation:
            # Use rotating file handler
            file_handler: logging.Handler = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
        else:
            # Use regular file handler
            file_handler = logging.FileHandler(log_path, encoding="utf-8")

        file_handler.setLevel(logging.DEBUG if dev_mode else logging.INFO)

        # Always use JSON format for file logging
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> ContextualLoggerAdapter:
    """Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        ContextualLoggerAdapter instance that includes operation context
    """
    # If the name is already under the vtt_transcribe namespace, use it as-is;
    # otherwise, create a child logger of the main vtt_transcribe logger.
    if name == "vtt_transcribe" or name.startswith("vtt_transcribe."):
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger(f"vtt_transcribe.{name}")

    return ContextualLoggerAdapter(logger, {})


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
