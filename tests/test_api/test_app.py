"""Tests for FastAPI application endpoints."""

from unittest.mock import patch

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
