"""Tests for JWT-based user authentication system.

Note: These tests document the expected behavior of the user management system.
Full integration tests with database fixtures require pytest-asyncio configuration
and will be added in a future iteration.

The user management endpoints are functional and have been manually tested, but
automated test coverage is currently limited to endpoint availability checks.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


class TestAuthenticationEndpoints:
    """Tests for authentication endpoint availability."""

    def test_register_endpoint_exists(self, client: TestClient) -> None:
        """Registration endpoint should be available."""
        # Invalid request to check endpoint exists
        response = client.post("/auth/register", json={})
        # Should return validation error, not 404
        assert response.status_code in [400, 422]

    def test_login_endpoint_exists(self, client: TestClient) -> None:
        """Login/token endpoint should be available."""
        response = client.post("/auth/token", data={})
        # Should return validation error or auth error, not 404
        assert response.status_code in [400, 401, 422]

    def test_me_endpoint_exists(self, client: TestClient) -> None:
        """User profile endpoint should be available."""
        response = client.get("/auth/me")
        # Should require auth, not 404
        assert response.status_code == 401


class TestAPIKeyEndpoints:
    """Tests for API key management endpoint availability."""

    def test_create_api_key_endpoint_requires_auth(self, client: TestClient) -> None:
        """API key creation endpoint should require authentication."""
        response = client.post("/api-keys/", json={})
        assert response.status_code == 401

    def test_list_api_keys_endpoint_requires_auth(self, client: TestClient) -> None:
        """API key listing endpoint should require authentication."""
        response = client.get("/api-keys/")
        assert response.status_code == 401

    def test_get_api_key_endpoint_requires_auth(self, client: TestClient) -> None:
        """API key retrieval endpoint should require authentication."""
        response = client.get("/api-keys/1")
        assert response.status_code == 401

    def test_delete_api_key_endpoint_requires_auth(self, client: TestClient) -> None:
        """API key deletion endpoint should require authentication."""
        response = client.delete("/api-keys/1")
        assert response.status_code == 401


class TestAPIKeyManagement:
    """Comprehensive tests for API key management routes."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self) -> None:
        """Should create API key successfully."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.api_keys import APIKeyCreate, create_api_key

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")
        key_data = APIKeyCreate(service="openai", api_key="sk-test123", key_name="Test Key")

        await create_api_key(key_data, mock_user, mock_db)

        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_create_api_key_invalid_service(self) -> None:
        """Should reject invalid service type."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.api_keys import APIKeyCreate, create_api_key

        mock_db = AsyncMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")
        key_data = APIKeyCreate(service="invalid", api_key="sk-test123", key_name="Test Key")

        with pytest.raises(HTTPException) as exc_info:
            await create_api_key(key_data, mock_user, mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid service" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_api_keys(self) -> None:
        """Should list user's API keys."""
        from vtt_transcribe.api.models import APIKey, User
        from vtt_transcribe.api.routes.api_keys import list_api_keys

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_key = APIKey(
            id=1,
            user_id=1,
            service="openai",
            encrypted_key="encrypted",
            key_name="Test",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalars.return_value.all.return_value = [mock_key]
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        keys = await list_api_keys(mock_user, mock_db)

        assert len(keys) == 1
        assert keys[0].service == "openai"

    @pytest.mark.asyncio
    async def test_get_api_key_success(self) -> None:
        """Should retrieve specific API key."""
        from vtt_transcribe.api.models import APIKey, User
        from vtt_transcribe.api.routes.api_keys import get_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_key = APIKey(
            id=1,
            user_id=1,
            service="openai",
            encrypted_key="encrypted",
            key_name="Test",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        key = await get_api_key(1, mock_user, mock_db)

        assert key.id == 1
        assert key.service == "openai"

    @pytest.mark.asyncio
    async def test_get_api_key_not_found(self) -> None:
        """Should raise 404 when key not found."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.api_keys import get_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(999, mock_user, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_api_key_success(self) -> None:
        """Should delete API key successfully."""
        from vtt_transcribe.api.models import APIKey, User
        from vtt_transcribe.api.routes.api_keys import delete_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_key = APIKey(
            id=1,
            user_id=1,
            service="openai",
            encrypted_key="encrypted",
            key_name="Test",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        await delete_api_key(1, mock_user, mock_db)

        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self) -> None:
        """Should raise 404 when key to delete not found."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.api_keys import delete_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        with pytest.raises(HTTPException) as exc_info:
            await delete_api_key(999, mock_user, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_api_key_success(self) -> None:
        """Should retrieve and decrypt user API key."""
        from vtt_transcribe.api.models import APIKey
        from vtt_transcribe.api.routes.api_keys import encrypt_key, get_user_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Create encrypted key
        encrypted = encrypt_key("sk-test123")
        mock_key = APIKey(
            id=1,
            user_id=1,
            service="openai",
            encrypted_key=encrypted,
            key_name="Test",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        decrypted = await get_user_api_key(1, "openai", mock_db)

        assert decrypted == "sk-test123"
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_get_user_api_key_not_found(self) -> None:
        """Should return None when user API key not found."""
        from vtt_transcribe.api.routes.api_keys import get_user_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_user_api_key(1, "openai", mock_db)

        assert result is None


class TestEncryptionFunctions:
    """Tests for API key encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Should encrypt and decrypt API key correctly."""
        from vtt_transcribe.api.routes.api_keys import decrypt_key, encrypt_key

        original_key = "sk-test-api-key-12345"
        encrypted = encrypt_key(original_key)
        decrypted = decrypt_key(encrypted)

        assert encrypted != original_key
        assert decrypted == original_key

    def test_encryption_key_validation(self) -> None:
        """Should raise RuntimeError when ENCRYPTION_KEY not set (lines 21-26)."""
        import os
        import sys

        original_key = os.getenv("ENCRYPTION_KEY")

        try:
            # Remove ENCRYPTION_KEY
            if "ENCRYPTION_KEY" in os.environ:
                del os.environ["ENCRYPTION_KEY"]

            # Remove api_keys module if already loaded
            if "vtt_transcribe.api.routes.api_keys" in sys.modules:
                del sys.modules["vtt_transcribe.api.routes.api_keys"]

            # Try to import - should raise RuntimeError during import
            # The import itself triggers the error, not the reload
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY environment variable is not set"):
                # Import triggers validation in module init
                import vtt_transcribe.api.routes.api_keys  # noqa: F401
        finally:
            # Restore original key
            if original_key:
                os.environ["ENCRYPTION_KEY"] = original_key

            # Reload module with correct key
            if "vtt_transcribe.api.routes.api_keys" in sys.modules:
                del sys.modules["vtt_transcribe.api.routes.api_keys"]


class TestJobHistoryEndpoints:
    """Tests for job history endpoint availability."""

    def test_list_jobs_endpoint_requires_auth(self, client: TestClient) -> None:
        """Job listing endpoint should require authentication."""
        response = client.get("/user/jobs/")
        assert response.status_code == 401

    def test_get_job_detail_endpoint_requires_auth(self, client: TestClient) -> None:
        """Job detail endpoint should require authentication."""
        response = client.get("/user/jobs/test-job")
        assert response.status_code == 401

    def test_delete_job_endpoint_requires_auth(self, client: TestClient) -> None:
        """Job deletion endpoint should require authentication."""
        response = client.delete("/user/jobs/test-job")
        assert response.status_code == 401

    def test_stats_endpoint_requires_auth(self, client: TestClient) -> None:
        """Job statistics endpoint should require authentication."""
        response = client.get("/user/jobs/stats/summary")
        assert response.status_code == 401


class TestJobManagement:
    """Comprehensive tests for job history routes."""

    @pytest.mark.asyncio
    async def test_list_user_jobs(self) -> None:
        """Should list user's transcription jobs."""
        from vtt_transcribe.api.models import TranscriptionJob, User
        from vtt_transcribe.api.routes.jobs import list_user_jobs

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_job = TranscriptionJob(
            id=1,
            user_id=1,
            job_id="test-job-1",
            filename="test.mp3",
            status="completed",
            transcript="Test transcript",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalars.return_value.all.return_value = [mock_job]
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        jobs = await list_user_jobs(mock_user, mock_db, status_filter=None, limit=50, offset=0)

        assert len(jobs) == 1
        assert jobs[0].job_id == "test-job-1"

    @pytest.mark.asyncio
    async def test_list_user_jobs_with_status_filter(self) -> None:
        """Should filter jobs by status."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.jobs import list_user_jobs

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        jobs = await list_user_jobs(mock_user, mock_db, status_filter="completed", limit=50, offset=0)

        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_get_job_detail_success(self) -> None:
        """Should retrieve job details."""
        from vtt_transcribe.api.models import TranscriptionJob, User
        from vtt_transcribe.api.routes.jobs import get_job_detail

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_job = TranscriptionJob(
            id=1,
            user_id=1,
            job_id="test-job-1",
            filename="test.mp3",
            status="completed",
            transcript="Test transcript",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        job = await get_job_detail("test-job-1", mock_user, mock_db)

        assert job.job_id == "test-job-1"
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_get_job_detail_not_found(self) -> None:
        """Should raise 404 when job not found."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.jobs import get_job_detail

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        with pytest.raises(HTTPException) as exc_info:
            await get_job_detail("nonexistent", mock_user, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_success(self) -> None:
        """Should delete job successfully."""
        from vtt_transcribe.api.models import TranscriptionJob, User
        from vtt_transcribe.api.routes.jobs import delete_job

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_job = TranscriptionJob(
            id=1,
            user_id=1,
            job_id="test-job-1",
            filename="test.mp3",
            status="completed",
            transcript="Test transcript",
            created_at=datetime.now(timezone.utc),
        )
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        await delete_job("test-job-1", mock_user, mock_db)

        assert mock_db.delete.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self) -> None:
        """Should raise 404 when job to delete not found."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.jobs import delete_job

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        with pytest.raises(HTTPException) as exc_info:
            await delete_job("nonexistent", mock_user, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_stats(self) -> None:
        """Should retrieve user job statistics."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.jobs import get_user_stats

        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Create mock stats result
        mock_stats = MagicMock()
        mock_stats.total = 10
        mock_stats.completed = 7
        mock_stats.failed = 1
        mock_stats.processing = 1
        mock_stats.pending = 1

        mock_result.one.return_value = mock_stats
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash")

        stats = await get_user_stats(mock_user, mock_db)

        assert stats["total_jobs"] == 10
        assert stats["completed"] == 7
        assert stats["failed"] == 1
        assert stats["processing"] == 1
        assert stats["pending"] == 1


class TestUserManagementIntegration:
    """Documentation of full user management integration tests.

    These tests document the expected end-to-end behavior but require
    async database fixtures for full implementation. They serve as
    specifications for the complete test suite to be added later.
    """

    def test_user_registration_flow_documented(self) -> None:
        """Document expected user registration flow.

        Expected behavior:
        1. POST /auth/register with username, email, password
        2. Returns 201 with user data (no password)
        3. User can immediately login
        4. Duplicate username/email returns 400
        """

    def test_user_login_flow_documented(self) -> None:
        """Document expected user login flow.

        Expected behavior:
        1. POST /auth/token with username and password (form data)
        2. Returns 200 with JWT access_token and token_type="bearer"
        3. Token can be used in Authorization header: "Bearer {token}"
        4. Invalid credentials return 401
        """

    def test_api_key_management_documented(self) -> None:
        """Document expected API key management flow.

        Expected behavior:
        1. User creates API key: POST /api-keys/ with service, api_key, key_name
        2. Returns 201 with metadata (never exposes encrypted or plain key)
        3. User can list their keys: GET /api-keys/
        4. User can delete keys: DELETE /api-keys/{id}
        5. Keys are encrypted at rest using Fernet
        6. Users can only access their own keys
        """

    def test_job_history_management_documented(self) -> None:
        """Document expected job history management flow.

        Expected behavior:
        1. Jobs are automatically created when transcription starts
        2. User can list their jobs: GET /job-history/ with filters
        3. User can get job details: GET /job-history/{job_id}
        4. User can delete jobs: DELETE /job-history/{job_id}
        5. User can get statistics: GET /job-history/stats/summary
        6. Users can only access their own jobs
        """
