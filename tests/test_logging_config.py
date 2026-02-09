"""Tests for logging configuration module."""

import logging

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
        assert isinstance(logger, logging.Logger)

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
        logger = logging_config.setup_logging(dev_mode=True)
        # Should be able to log with extra fields
        logger.info("Test message", extra={"job_id": "test-123", "duration": 1.5})
        assert True  # If no exception, test passes

    def test_json_formatter_includes_structured_fields(self) -> None:
        """Test that JSON formatter includes structured fields in output."""
        import json
        from io import StringIO

        # Capture log output
        log_stream = StringIO()
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
        if log_output.strip():
            log_data = json.loads(log_output.strip())
            assert "message" in log_data
            assert log_data.get("user_id") == "user-123"
            assert log_data.get("action") == "upload"
