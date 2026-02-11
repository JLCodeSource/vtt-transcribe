"""Comprehensive tests for API routes to achieve 100% coverage."""

import contextlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


class TestAuthRoutes:
    """Tests for authentication routes."""

    @pytest.mark.asyncio
    async def test_register_user_success(self) -> None:
        """Should register a new user successfully."""
        from vtt_transcribe.api.routes.auth import register

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        from vtt_transcribe.api.routes.auth import UserCreate

        user_data = UserCreate(username="newuser", email="new@example.com", password="password123")

        with patch("vtt_transcribe.api.routes.auth.get_password_hash") as mock_hash:
            mock_hash.return_value = "hashed_password"

            await register(user_data, mock_db)

            assert mock_db.add.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self) -> None:
        """Should reject duplicate username."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.auth import UserCreate, register

        mock_db = AsyncMock()
        mock_result = MagicMock()
        existing_user = User(id=1, username="existing", email="other@example.com", hashed_password="hash")
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        user_data = UserCreate(username="existing", email="new@example.com", password="password123")

        with pytest.raises(HTTPException) as exc_info:
            await register(user_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Username already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self) -> None:
        """Should reject duplicate email."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.auth import UserCreate, register

        mock_db = AsyncMock()

        # First call (username check) returns None, second call (email check) returns user
        mock_result_username = MagicMock()
        mock_result_username.scalar_one_or_none.return_value = None

        mock_result_email = MagicMock()
        existing_user = User(id=1, username="other", email="existing@example.com", hashed_password="hash")
        mock_result_email.scalar_one_or_none.return_value = existing_user

        mock_db.execute = AsyncMock(side_effect=[mock_result_username, mock_result_email])

        user_data = UserCreate(username="newuser", email="existing@example.com", password="password123")

        with pytest.raises(HTTPException) as exc_info:
            await register(user_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        """Should return token on successful login."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.auth import login

        mock_db = AsyncMock()
        mock_form = MagicMock()
        mock_form.username = "testuser"
        mock_form.password = "password123"

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash", is_active=True)

        with patch("vtt_transcribe.api.routes.auth.authenticate_user") as mock_auth:
            with patch("vtt_transcribe.api.routes.auth.create_access_token") as mock_token:
                mock_auth.return_value = mock_user
                mock_token.return_value = "fake-jwt-token"

                token = await login(mock_form, mock_db)

                assert token.access_token == "fake-jwt-token"
                assert token.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self) -> None:
        """Should reject invalid credentials."""
        from vtt_transcribe.api.routes.auth import login

        mock_db = AsyncMock()
        mock_form = MagicMock()
        mock_form.username = "testuser"
        mock_form.password = "wrongpassword"

        with patch("vtt_transcribe.api.routes.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await login(mock_form, mock_db)

            assert exc_info.value.status_code == 401
            assert "Incorrect username or password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_read_users_me(self) -> None:
        """Should return current user information."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.auth import read_users_me

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash", is_active=True)

        user = await read_users_me(mock_user)

        assert user.username == "testuser"
        assert user.email == "test@example.com"


class TestAPIKeyRoutes:
    """Tests for API key management routes."""

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


class TestJobRoutes:
    """Tests for job history routes."""

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
    async def test_init_db_not_available(self) -> None:
        """Should skip init when database not available."""
        from vtt_transcribe.api.database import init_db

        with patch("vtt_transcribe.api.database.database_available", False):
            # Should not raise error
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
                try:
                    msg = "Test error"
                    raise ValueError(msg)
                except ValueError:
                    with contextlib.suppress(ValueError, StopAsyncIteration):
                        await generator.athrow(ValueError, ValueError("Test error"), None)

                # Rollback should be called
                assert mock_session.rollback.called


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
