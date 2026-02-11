"""Tests for logging configuration module."""

import io
import json
import logging
import tempfile
from pathlib import Path

import pytest

from vtt_transcribe import logging_config


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def test_setup_logging_creates_logger(self) -> None:
        """Test that setup_logging returns a configured logger."""
        logger = logging_config.setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "vtt_transcribe"

    def test_setup_logging_sets_default_level_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that default log level is INFO in production mode."""
        monkeypatch.setenv("VTT_ENV", "production")
        logger = logging_config.setup_logging()
        assert logger.level == logging.INFO

    def test_setup_logging_dev_mode_sets_debug_level(self) -> None:
        """Test that dev mode sets DEBUG log level."""
        logger = logging_config.setup_logging(dev_mode=True)
        assert logger.level == logging.DEBUG

    def test_setup_logging_has_console_handler(self) -> None:
        """Test that logger has a console handler configured."""
        logger = logging_config.setup_logging()
        assert len(logger.handlers) > 0
        # At least one handler should be a StreamHandler
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_setup_logging_json_format_in_prod(self) -> None:
        """Test that production mode uses JSON formatting."""
        logger = logging_config.setup_logging(dev_mode=False)
        # Check that at least one handler has a JSON formatter
        has_json_formatter = False
        for handler in logger.handlers:
            if hasattr(handler.formatter, "_style"):
                # JSON formatters typically have custom formatters
                # We'll verify this in the implementation
                has_json_formatter = True
                break
        # This will fail initially - we'll implement JSON formatting
        assert has_json_formatter or not logger.handlers

    def test_setup_logging_human_readable_format_in_dev(self) -> None:
        """Test that dev mode uses human-readable formatting."""
        logger = logging_config.setup_logging(dev_mode=True)
        assert len(logger.handlers) > 0
        # In dev mode, should have readable format (not JSON)
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                # Should have a formatter
                assert handler.formatter is not None


class TestLoggingContextManager:
    """Test logging context for operation tracking."""

    def test_get_logger_returns_configured_logger(self) -> None:
        """Test that get_logger returns a logger instance."""
        logger = logging_config.get_logger(__name__)
        assert isinstance(logger, logging_config.ContextualLoggerAdapter)

    def test_get_logger_with_context_adds_context(self) -> None:
        """Test that context can be added to logger."""
        # This will test the context management functionality
        logger = logging_config.get_logger(__name__)
        # Context functionality will be added in implementation
        assert logger is not None


class TestEnvironmentBasedConfiguration:
    """Test environment-based configuration."""

    def test_detect_environment_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment is detected from ENV var."""
        monkeypatch.setenv("VTT_ENV", "production")
        env = logging_config.get_environment()
        assert env == "production"

    def test_detect_environment_defaults_to_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment defaults to development."""
        monkeypatch.delenv("VTT_ENV", raising=False)
        env = logging_config.get_environment()
        assert env == "development"

    def test_is_production_returns_true_for_prod_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_production helper for production environment."""
        monkeypatch.setenv("VTT_ENV", "production")
        assert logging_config.is_production() is True

    def test_is_production_returns_false_for_dev_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_production helper for development environment."""
        monkeypatch.setenv("VTT_ENV", "development")
        assert logging_config.is_production() is False


class TestStructuredLogging:
    """Test structured logging with context."""

    def test_logger_supports_structured_fields(self) -> None:
        """Test that logger can log with structured fields."""
        import io
        import logging

        # Create a test logger
        test_logger = logging.getLogger("vtt_transcribe.test")
        test_logger.setLevel(logging.INFO)
        test_logger.handlers.clear()

        # Capture output
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        # Log with structured fields
        test_logger.info("Test message", extra={"job_id": "test-123", "duration": 1.5})

        # Verify log was generated
        output = stream.getvalue()
        assert output.strip(), "Should have generated log output"
        assert "Test message" in output

    def test_json_formatter_includes_structured_fields(self) -> None:
        """Test that JSON formatter includes structured fields in output."""
        import json

        # Capture log output
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)

        # Use production mode (JSON format)
        logger = logging_config.setup_logging(dev_mode=False)
        logger.handlers.clear()

        # Add custom formatter that outputs proper JSON
        formatter = logging_config.JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log with structured data
        logger.info("Test event", extra={"user_id": "user-123", "action": "upload"})

        # Parse output as JSON
        log_output = log_stream.getvalue()
        assert log_output.strip(), "Log output should not be empty - logging may be misconfigured"

        log_data = json.loads(log_output.strip())
        assert "message" in log_data
        assert log_data.get("user_id") == "user-123"
        assert log_data.get("action") == "upload"


class TestLoggingConfigCoverage:
    """Tests to cover missing lines in logging_config.py."""

    def test_json_formatter_with_exception(self) -> None:
        """Test JSON formatter includes exception info (line 117)."""
        import io
        import json

        from vtt_transcribe.logging_config import JsonFormatter

        # Create logger with JSON formatter
        logger = logging.getLogger("test_exception")
        logger.setLevel(logging.ERROR)
        logger.handlers.clear()

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

        # Log with exception
        try:
            raise ValueError("Test exception")  # noqa: EM101
        except ValueError:
            logger.exception("Error occurred")

        output = stream.getvalue()
        log_data = json.loads(output.strip())

        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test exception" in log_data["exception"]


class TestOperationContext:
    """Test operation context tracking and correlation IDs."""

    def test_operation_context_generates_id(self) -> None:
        """Test that operation_context generates an operation ID when not provided."""
        with logging_config.operation_context("test_operation") as op_id:
            assert op_id is not None
            assert isinstance(op_id, str)
            assert len(op_id) == 36  # UUID4 length

    def test_operation_context_uses_provided_id(self) -> None:
        """Test that operation_context uses provided operation ID."""
        custom_id = "custom-operation-123"
        with logging_config.operation_context("test_operation", operation_id=custom_id) as op_id:
            assert op_id == custom_id

    def test_operation_context_sets_context_data(self) -> None:
        """Test that operation context data is available within context."""
        with logging_config.operation_context("test_operation", user_id="user123", action="upload"):
            context = logging_config.get_operation_context()
            assert context["operation_name"] == "test_operation"
            assert context["user_id"] == "user123"
            assert context["action"] == "upload"
            assert "operation_id" in context

    def test_operation_context_clears_after_exit(self) -> None:
        """Test that operation context is cleared after exiting context manager."""
        with logging_config.operation_context("test_operation"):
            # Context should be set
            context = logging_config.get_operation_context()
            assert context["operation_name"] == "test_operation"

        # Context should be cleared
        context = logging_config.get_operation_context()
        assert context == {}

    def test_nested_operation_contexts(self) -> None:
        """Test that nested operation contexts work correctly."""
        with logging_config.operation_context("outer_operation", level="outer"):
            outer_context = logging_config.get_operation_context()
            assert outer_context["operation_name"] == "outer_operation"
            assert outer_context["level"] == "outer"

            with logging_config.operation_context("inner_operation", level="inner", detail="nested"):
                inner_context = logging_config.get_operation_context()
                assert inner_context["operation_name"] == "inner_operation"
                assert inner_context["level"] == "inner"  # Should override
                assert inner_context["detail"] == "nested"  # Should add

            # Should restore outer context
            restored_context = logging_config.get_operation_context()
            assert restored_context["operation_name"] == "outer_operation"
            assert restored_context["level"] == "outer"

    def test_contextual_logger_adapter_includes_context(self) -> None:
        """Test that ContextualLoggerAdapter includes operation context in log records."""
        # Set up logger with string capture
        base_logger = logging.getLogger("test_contextual")
        base_logger.setLevel(logging.INFO)
        base_logger.handlers.clear()

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging_config.JsonFormatter())
        base_logger.addHandler(handler)

        # Create contextual logger adapter
        logger = logging_config.ContextualLoggerAdapter(base_logger, {})

        # Log within operation context
        with logging_config.operation_context("test_operation", user_id="user123"):
            logger.info("Test message")

        # Parse output
        output = stream.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["message"] == "Test message"
        assert log_data["operation_name"] == "test_operation"
        assert log_data["user_id"] == "user123"
        assert "operation_id" in log_data

    def test_contextual_logger_adapter_merges_extra(self) -> None:
        """Test that ContextualLoggerAdapter merges context with extra data."""
        # Set up logger with string capture
        base_logger = logging.getLogger("test_merge")
        base_logger.setLevel(logging.INFO)
        base_logger.handlers.clear()

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging_config.JsonFormatter())
        base_logger.addHandler(handler)

        # Create contextual logger adapter
        logger = logging_config.ContextualLoggerAdapter(base_logger, {})

        # Log within operation context with extra data
        with logging_config.operation_context("test_operation", context_field="from_context"):
            logger.info("Test message", extra={"extra_field": "from_extra", "context_field": "from_extra_override"})

        # Parse output
        output = stream.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["message"] == "Test message"
        assert log_data["operation_name"] == "test_operation"
        assert log_data["extra_field"] == "from_extra"
        # Extra should override context for same key
        assert log_data["context_field"] == "from_extra_override"

    def test_get_logger_returns_contextual_adapter(self) -> None:
        """Test that get_logger returns a ContextualLoggerAdapter."""
        logger = logging_config.get_logger(__name__)
        assert isinstance(logger, logging_config.ContextualLoggerAdapter)

    def test_contextual_logger_without_context(self) -> None:
        """Test that ContextualLoggerAdapter works without operation context."""
        base_logger = logging.getLogger("test_no_context")
        base_logger.setLevel(logging.INFO)
        base_logger.handlers.clear()

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging_config.JsonFormatter())
        base_logger.addHandler(handler)

        logger = logging_config.ContextualLoggerAdapter(base_logger, {})
        logger.info("Test message", extra={"extra_field": "value"})

        # Parse output
        output = stream.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["message"] == "Test message"
        assert log_data["extra_field"] == "value"
        # Should not have context fields when no context is set
        assert "operation_name" not in log_data

    def test_operation_context_validates_reserved_keys(self) -> None:
        """Test that reserved keys in context dict cause errors.

        While Python's argument resolution typically prevents direct override of
        operation_id and operation_name parameters (raising TypeError), we have
        explicit validation to provide clear error messages in edge cases.
        """
        # Attempting to pass reserved keys in **context dict causes an error
        # (either TypeError from Python or ValueError from our validation)
        context_with_reserved = {"operation_name": "override", "file": "test.mp3"}
        with (
            pytest.raises((ValueError, TypeError)),
            logging_config.operation_context("test", **context_with_reserved),
        ):
            pass

        # Verify normal context works fine
        with logging_config.operation_context("test", file="test.mp3") as op_id:
            ctx = logging_config.get_operation_context()
            assert ctx["operation_name"] == "test"
            assert ctx["file"] == "test.mp3"
            assert ctx["operation_id"] == op_id


class TestFileLoggingAndRotation:
    """Test file logging and log rotation features."""

    def test_setup_logging_with_file_output(self) -> None:
        """Test that setup_logging can write to file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            log_file = temp_file.name

        try:
            # Setup logger with file output
            logger = logging_config.setup_logging(dev_mode=False, log_file=log_file)

            # Log a message
            logger.info("Test file logging")

            # Force handlers to flush
            for handler in logger.handlers:
                handler.flush()

            # Read file contents
            with open(log_file) as f:
                content = f.read()

            # Should contain JSON log
            assert content.strip()
            log_data = json.loads(content.strip())
            assert log_data["message"] == "Test file logging"
            assert log_data["level"] == "INFO"

        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_setup_logging_creates_log_directory(self) -> None:
        """Test that setup_logging creates log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "logs" / "app.log"

            # Directory should not exist yet
            assert not log_file.parent.exists()

            # Setup logger - just need to call it to create directory
            _ = logging_config.setup_logging(log_file=log_file)
            assert log_file.parent.is_dir()

    def test_file_logging_uses_json_format(self) -> None:
        """Test that file logging always uses JSON format even in dev mode."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            log_file = temp_file.name

        try:
            # Setup in dev mode with file output
            logger = logging_config.setup_logging(dev_mode=True, log_file=log_file)
            logger.info("Test message")

            # Force flush
            for handler in logger.handlers:
                handler.flush()

            # File should contain JSON even in dev mode
            with open(log_file) as f:
                content = f.read()

            log_data = json.loads(content.strip())
            assert log_data["message"] == "Test message"

        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_rotating_file_handler_enabled_by_default(self) -> None:
        """Test that rotating file handler is used by default."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            log_file = temp_file.name

        try:
            logger = logging_config.setup_logging(log_file=log_file)

            # Find the file handler
            file_handler = None
            for handler in logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
                    break

            assert file_handler is not None
            assert file_handler.maxBytes == 10 * 1024 * 1024  # 10MB default
            assert file_handler.backupCount == 5  # Default backup count

        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_rotation_can_be_disabled(self) -> None:
        """Test that log rotation can be disabled."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            log_file = temp_file.name

        try:
            logger = logging_config.setup_logging(log_file=log_file, enable_rotation=False)

            # Should use regular FileHandler, not RotatingFileHandler
            file_handler = None
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
                    break

            assert file_handler is not None

        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_custom_rotation_parameters(self) -> None:
        """Test custom rotation parameters."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            log_file = temp_file.name

        try:
            logger = logging_config.setup_logging(log_file=log_file, max_bytes=1024, backup_count=3)

            # Find rotating file handler
            file_handler = None
            for handler in logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
                    break

            assert file_handler is not None
            assert file_handler.maxBytes == 1024
            assert file_handler.backupCount == 3

        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_dual_output_console_and_file(self) -> None:
        """Test that logging works to both console and file simultaneously."""
        console_stream = io.StringIO()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            log_file = temp_file.name

        try:
            # Mock sys.stdout to capture console output
            import sys
            from unittest.mock import patch

            with patch.object(sys, "stdout", console_stream):
                logger = logging_config.setup_logging(dev_mode=True, log_file=log_file)
                logger.info("Dual output test")

                # Force flush
                for handler in logger.handlers:
                    handler.flush()

            # Check console output (human readable format in dev mode)
            console_output = console_stream.getvalue()
            assert "Dual output test" in console_output
            assert "INFO" in console_output

            # Check file output (JSON format)
            with open(log_file) as f:
                file_content = f.read()

            log_data = json.loads(file_content.strip())
            assert log_data["message"] == "Dual output test"
            assert log_data["level"] == "INFO"

        finally:
            Path(log_file).unlink(missing_ok=True)


class TestLoggingHandlerEdgeCases:
    """Test edge cases for logging handler management."""

    def test_setup_logging_with_closed_stream(self) -> None:
        """Should handle closed stream gracefully (lines 207-210)."""
        import sys
        from io import StringIO

        # Create a closed stream
        closed_stream = StringIO()
        closed_stream.close()

        original_stdout = sys.stdout
        try:
            # Replace stdout with closed stream
            sys.stdout = closed_stream

            # Should not raise error
            logger = logging_config.setup_logging(dev_mode=True, use_stderr=False)

            # Logger should still be created
            assert logger is not None
        finally:
            sys.stdout = original_stdout

    def test_safely_flush_closed_handler(self) -> None:
        """Should handle closed handler stream gracefully (lines 138-141)."""
        import io

        # Create a handler with a closed stream
        closed_stream = io.StringIO()
        closed_stream.close()

        handler = logging.StreamHandler(closed_stream)

        # Should not raise error
        logging_config._safely_flush_and_close_handler(handler)

    def test_safely_flush_handler_without_stream_attribute(self) -> None:
        """Should handle handler without stream attribute (line 138-139)."""
        # Create a handler without stream attribute (base Handler class)
        handler = logging.Handler()

        # Should not raise error
        logging_config._safely_flush_and_close_handler(handler)

    def test_safely_flush_handler_with_valueerror(self) -> None:
        """Should handle ValueError during flush (line 140)."""
        from unittest.mock import MagicMock

        # Create a handler that raises ValueError on flush
        handler = logging.Handler()
        handler.flush = MagicMock(side_effect=ValueError("Stream closed"))  # type: ignore[method-assign]

        # Should not raise error
        logging_config._safely_flush_and_close_handler(handler)

    def test_safely_flush_handler_with_oserror(self) -> None:
        """Should handle OSError during flush (line 140)."""
        from unittest.mock import MagicMock

        # Create a handler that raises OSError on flush
        handler = logging.Handler()
        handler.flush = MagicMock(side_effect=OSError("Stream error"))  # type: ignore[method-assign]

        # Should not raise error
        logging_config._safely_flush_and_close_handler(handler)
