"""Tests for FastAPI application endpoints."""

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint_exists(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_status(self, client):
        """Health endpoint should return status in JSON."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_returns_version(self, client):
        """Health endpoint should return application version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint_exists(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_returns_welcome_message(self, client):
        """Root endpoint should return welcome message."""
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "vtt-transcribe" in data["message"].lower()


class TestAPIMetadata:
    """Tests for API metadata and documentation."""

    def test_openapi_schema_exists(self, client):
        """OpenAPI schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data

    def test_api_title_in_schema(self, client):
        """API should have proper title in OpenAPI schema."""
        response = client.get("/openapi.json")
        data = response.json()
        assert data["info"]["title"] == "vtt-transcribe API"

    def test_api_version_in_schema(self, client):
        """API should have version in OpenAPI schema."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "version" in data["info"]


class TestAPIServerCoverage:
    """Tests to cover api/server.py."""

    def test_server_main_function(self) -> None:
        """Test server.py main function."""
        with patch("vtt_transcribe.api.server.uvicorn.run") as mock_run:
            from vtt_transcribe.api.server import main

            main()

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["host"] == "0.0.0.0"  # noqa: S104
            assert call_args[1]["port"] == 8000
            assert call_args[1]["reload"] is True


class TestAPIServer100Coverage:
    """Tests to achieve 100% coverage on api/server.py."""

    def test_server_imports_and_main(self) -> None:
        """Test server.py imports and main() function."""
        with patch("vtt_transcribe.api.server.uvicorn.run") as mock_run:
            # Force reimport to ensure coverage
            import sys

            if "vtt_transcribe.api.server" in sys.modules:
                del sys.modules["vtt_transcribe.api.server"]

            from vtt_transcribe.api.server import main

            main()

            mock_run.assert_called_once()


class TestServerMainBlock:
    """Tests to cover server.py __main__ block."""

    def test_server_main_block_import(self) -> None:
        """Test the if __name__ == '__main__' block (line 17)."""
        import subprocess
        import sys

        # Create a test script that imports and checks the module
        test_script = """
import sys
from unittest.mock import patch

# Mock uvicorn before importing
with patch("vtt_transcribe.api.server.uvicorn"):
    # Import the module to ensure all lines are executed
    import vtt_transcribe.api.server
  # noqa: W293
    # Check that main function exists
    assert hasattr(vtt_transcribe.api.server, "main")
  # noqa: W293
    print("SUCCESS")
"""

        # Run the script
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    def test_server_module_direct_execution(self) -> None:
        """Test running server.py directly as a module."""
        import subprocess
        import sys

        # Run the module with mocked uvicorn
        code = """
import sys
from unittest.mock import patch, MagicMock

# Mock uvicorn.run to prevent actual server start
mock_run = MagicMock()
with patch('uvicorn.run', mock_run):
    # This should trigger __main__ block
    import runpy
    try:
        runpy.run_module('vtt_transcribe.api.server', run_name='__main__')
    except SystemExit:
        pass  # Expected when main() completes
  # noqa: W293
    # Verify uvicorn.run was called
    assert mock_run.called, "uvicorn.run should have been called"
    print("MAIN_BLOCK_EXECUTED")
"""

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Check if the main block was executed
        assert "MAIN_BLOCK_EXECUTED" in result.stdout or result.returncode == 0


def test_server_main_block_coverage() -> None:
    """Test the if __name__ == '__main__' block in server.py (line 17)."""
    import runpy
    import sys

    # Mock uvicorn.run to prevent actual server start
    with patch("uvicorn.run") as mock_run:
        # Temporarily remove server module to force reimport
        if "vtt_transcribe.api.server" in sys.modules:
            del sys.modules["vtt_transcribe.api.server"]

        # Run the module as __main__ to execute line 17
        try:  # noqa: SIM105
            runpy.run_module("vtt_transcribe.api.server", run_name="__main__")
        except SystemExit:
            pass  # Expected when main() completes

        # Verify main() was called (which calls uvicorn.run)
        assert mock_run.called


class TestAPIAppLifespan:
    """Test vtt_transcribe/api/app.py lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_init_db_error_suppressed(self) -> None:
        """Should suppress database initialization errors."""
        from vtt_transcribe.api.app import lifespan

        # Mock app object
        mock_app = MagicMock()

        # Mock init_db to raise an error
        with patch("vtt_transcribe.api.app.init_db", side_effect=Exception("DB error")):
            # lifespan uses contextlib.suppress, so errors should be suppressed
            async with lifespan(mock_app):
                # Should not raise error even though init_db failed
                pass

            # Success if no exception was raised


class TestAPIModels:
    """Test vtt_transcribe/api/models.py __repr__ methods."""

    def test_user_repr(self) -> None:
        """Should generate readable repr for User."""
        from vtt_transcribe.api.models import User

        user = User(id=1, username="test", email="test@example.com", hashed_password="hash")
        repr_str = repr(user)

        assert "<User(" in repr_str
        assert "test" in repr_str

    def test_api_key_repr(self) -> None:
        """Should generate readable repr for APIKey."""
        from vtt_transcribe.api.models import APIKey

        key = APIKey(id=1, user_id=1, service="openai", encrypted_key="encrypted", key_name="test")
        repr_str = repr(key)

        assert "<APIKey(" in repr_str

    def test_transcription_job_repr(self) -> None:
        """Should generate readable repr for TranscriptionJob."""
        from vtt_transcribe.api.models import TranscriptionJob

        job = TranscriptionJob(id=1, user_id=1, job_id="test-123", filename="test.mp3", status="completed")
        repr_str = repr(job)

        assert "<TranscriptionJob(" in repr_str
        assert "test-123" in repr_str


class TestDatabaseConfiguration:
    """Test database URL configuration and conversion."""

    def test_postgresql_url_conversion(self) -> None:
        """Should convert postgresql:// to postgresql+asyncpg:// (lines 15-16)."""
        import os

        original_url = os.getenv("DATABASE_URL")

        try:
            # Set PostgreSQL URL
            os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"

            # Reload database module to trigger URL conversion
            import importlib

            import vtt_transcribe.api.database

            importlib.reload(vtt_transcribe.api.database)

            # Check conversion happened
            assert vtt_transcribe.api.database.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"
        finally:
            # Restore original
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

            # Reload again to restore state
            import importlib

            import vtt_transcribe.api.database

            importlib.reload(vtt_transcribe.api.database)

    def test_sqlite_url_conversion(self) -> None:
        """Should convert sqlite:// to sqlite+aiosqlite:// (line 17)."""
        import os

        original_url = os.getenv("DATABASE_URL")

        try:
            # Set SQLite URL
            os.environ["DATABASE_URL"] = "sqlite:///./test.db"

            # Reload database module to trigger URL conversion
            import importlib

            import vtt_transcribe.api.database

            importlib.reload(vtt_transcribe.api.database)

            # Check conversion happened
            assert vtt_transcribe.api.database.DATABASE_URL == "sqlite+aiosqlite:///./test.db"
        finally:
            # Restore original
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

            # Reload again to restore state
            import importlib

            import vtt_transcribe.api.database

            importlib.reload(vtt_transcribe.api.database)

    @pytest.mark.asyncio
    async def test_get_db_finally_closes_session(self) -> None:
        """Should close session in finally block (line 74)."""
        from vtt_transcribe.api.database import get_db

        with patch("vtt_transcribe.api.database.database_available", True):
            with patch("vtt_transcribe.api.database.AsyncSessionLocal") as mock_session_maker:
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.close = AsyncMock()
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context.__aexit__ = AsyncMock()
                mock_session_maker.return_value = mock_context

                # Use the generator
                generator = get_db()
                await generator.__anext__()

                # Manually close the generator to trigger finally block
                import contextlib

                with contextlib.suppress(StopAsyncIteration):
                    await generator.aclose()

                # Close should have been called
                assert mock_session.close.called


class TestDatabaseFunctions:
    """Tests for database utility functions."""

    @pytest.mark.asyncio
    async def test_init_db_success(self) -> None:
        """Should initialize database tables successfully."""
        from vtt_transcribe.api.database import init_db

        with patch("vtt_transcribe.api.database.database_available", True):
            with patch("vtt_transcribe.api.database.engine") as mock_engine:
                mock_conn = AsyncMock()
                mock_conn.run_sync = AsyncMock()
                # Create proper async context manager
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_engine.begin.return_value = mock_context

                await init_db()

                assert mock_conn.run_sync.called

    @pytest.mark.asyncio
    async def test_init_db_when_unavailable(self) -> None:
        """Should return early if database_available is False."""
        from vtt_transcribe.api.database import init_db

        with patch("vtt_transcribe.api.database.database_available", False):
            # Should not raise error, just return
            await init_db()

    @pytest.mark.asyncio
    async def test_get_db_not_available(self) -> None:
        """Should raise error when database not available."""
        from vtt_transcribe.api.database import get_db

        with patch("vtt_transcribe.api.database.database_available", False):
            with pytest.raises(RuntimeError) as exc_info:
                async for _ in get_db():
                    pass

            assert "Database dependencies not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_error(self) -> None:
        """Should rollback session on exception."""
        from vtt_transcribe.api.database import get_db

        with patch("vtt_transcribe.api.database.database_available", True):
            with patch("vtt_transcribe.api.database.AsyncSessionLocal") as mock_session_maker:
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.rollback = AsyncMock()
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context.__aexit__ = AsyncMock()
                mock_session_maker.return_value = mock_context

                # Test exception handling
                generator = get_db()
                _session = await generator.__anext__()

                # Simulate exception by calling athrow
                msg = "Test error"
                with contextlib.suppress(ValueError, StopAsyncIteration):
                    await generator.athrow(ValueError(msg))

                # Rollback should be called
                assert mock_session.rollback.called

    @pytest.mark.asyncio
    async def test_get_db_with_exception(self) -> None:
        """Should handle exceptions in database session."""
        from vtt_transcribe.api.database import get_db

        with patch("vtt_transcribe.api.database.database_available", True):
            with patch("vtt_transcribe.api.database.AsyncSessionLocal") as mock_session_maker:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.rollback = AsyncMock()
                mock_session_maker.return_value = mock_session

                # Test exception handling
                generator = get_db()
                await generator.__anext__()

                # Simulate exception
                msg = "Test error"
                try:
                    raise ValueError(msg)
                except ValueError:
                    with contextlib.suppress(ValueError, StopAsyncIteration):
                        await generator.athrow(ValueError(msg))

                # Rollback should be called
                assert mock_session.rollback.called
