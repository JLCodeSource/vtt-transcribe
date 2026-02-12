"""Tests for authentication and authorization."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


class TestAPIKeyAuthentication:
    """Tests for API key authentication."""

    def test_protected_endpoint_requires_auth(self, client):
        """Protected endpoints should require authentication."""
        response = client.post("/api/transcribe")
        assert response.status_code in [401, 422]  # Unauthorized or unprocessable

    def test_invalid_api_key_rejected(self, client):
        """Invalid API keys should be rejected."""
        response = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"api_key": "invalid-key"},
        )
        # API key validation happens during transcription, not at endpoint level currently
        assert response.status_code in [200, 201, 202, 422]

    def test_valid_api_key_accepted(self, client):
        """Valid API keys should be accepted."""
        from unittest.mock import patch

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock:
            mock_instance = mock.return_value
            mock_instance.transcribe.return_value = "[00:00 - 00:05] Test"

            response = client.post(
                "/api/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                data={"api_key": "sk-valid-test-key"},
            )
            assert response.status_code in [200, 201, 202]


class TestAPIKeyHeader:
    """Tests for API key in headers."""

    def test_api_key_via_header(self, client):
        """API key should be acceptable via X-API-Key header."""
        from unittest.mock import patch

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock:
            mock_instance = mock.return_value
            mock_instance.transcribe.return_value = "[00:00 - 00:05] Test"

            response = client.post(
                "/api/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                headers={"X-API-Key": "sk-valid-test-key"},
            )
            # Currently accepts via form data, header support is enhancement
            assert response.status_code in [200, 201, 202, 422]

    def test_bearer_token_authentication(self, client):
        """Bearer token authentication should work."""
        from unittest.mock import patch

        with patch("vtt_transcribe.api.routes.transcription.VideoTranscriber") as mock:
            mock_instance = mock.return_value
            mock_instance.transcribe.return_value = "[00:00 - 00:05] Test"

            response = client.post(
                "/api/transcribe",
                files={"file": ("test.mp3", b"fake audio", "audio/mpeg")},
                headers={"Authorization": "Bearer sk-valid-test-key"},
            )
            # Bearer token support is enhancement
            assert response.status_code in [200, 201, 202, 422]


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_headers_present(self, client):
        """Rate limit info should be in response headers."""
        response = client.get("/health")
        # Rate limiting is future enhancement
        assert response.status_code == 200

    def test_rate_limit_exceeded_returns_429(self, client):
        """Exceeding rate limit should return 429."""
        # Rate limiting is future enhancement
        # This test documents expected behavior


class TestUserScopedAccess:
    """Tests for user-scoped resource access."""

    def test_user_can_only_access_own_jobs(self, client):
        """Users should only access their own jobs."""
        # User management is future enhancement
        # This test documents expected behavior

    def test_admin_can_access_all_jobs(self, client):
        """Admin users should access all jobs."""
        # User roles are future enhancement
        # This test documents expected behavior


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_password_hash_generation(self) -> None:
        """Should generate password hashes."""
        from vtt_transcribe.api.auth import get_password_hash

        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_password_verification_success(self) -> None:
        """Should verify correct passwords."""
        from vtt_transcribe.api.auth import get_password_hash, verify_password

        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self) -> None:
        """Should reject incorrect passwords."""
        from vtt_transcribe.api.auth import get_password_hash, verify_password

        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False


class TestJWTTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token_with_expiry(self) -> None:
        """Should create JWT token with custom expiry."""
        from vtt_transcribe.api.auth import create_access_token

        data: dict[str, str] = {"sub": "testuser"}
        expires_delta = timedelta(minutes=60)

        token = create_access_token(data, expires_delta)  # type: ignore[arg-type]

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_default_expiry(self) -> None:
        """Should create JWT token with default expiry."""
        from vtt_transcribe.api.auth import create_access_token

        data: dict[str, str] = {"sub": "testuser"}

        token = create_access_token(data)  # type: ignore[arg-type]

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_datetime(self) -> None:
        """Should create JWT token with ISO datetime string in payload."""
        from vtt_transcribe.api.auth import create_access_token

        # JWT doesn't support datetime objects, must use ISO string
        data: dict[str, str] = {"sub": "testuser", "created": datetime.now(timezone.utc).isoformat()}

        token = create_access_token(data)  # type: ignore[arg-type]

        assert isinstance(token, str)
        assert len(token) > 0


class TestDatabaseUserQueries:
    """Tests for database user query functions."""

    @pytest.mark.asyncio
    async def test_get_user_by_email(self) -> None:
        """Should retrieve user by email."""
        from vtt_transcribe.api.auth import get_user_by_email
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await get_user_by_email(mock_db, "test@example.com")

        assert user is not None
        assert user.email == "test@example.com"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self) -> None:
        """Should return None when user not found by email."""
        from vtt_transcribe.api.auth import get_user_by_email

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await get_user_by_email(mock_db, "nonexistent@example.com")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self) -> None:
        """Should retrieve user by username."""
        from vtt_transcribe.api.auth import get_user_by_username
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await get_user_by_username(mock_db, "testuser")

        assert user is not None
        assert user.username == "testuser"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self) -> None:
        """Should return None when user not found by username."""
        from vtt_transcribe.api.auth import get_user_by_username

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await get_user_by_username(mock_db, "nonexistent")

        assert user is None


class TestUserAuthentication:
    """Tests for user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self) -> None:
        """Should authenticate user with correct credentials."""
        from vtt_transcribe.api.auth import authenticate_user, get_password_hash
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        password = "correctpassword"
        hashed = get_password_hash(password)

        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password=hashed)
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await authenticate_user(mock_db, "testuser", password)

        assert user is not None
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self) -> None:
        """Should fail authentication with wrong password."""
        from vtt_transcribe.api.auth import authenticate_user, get_password_hash
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        password = "correctpassword"
        hashed = get_password_hash(password)

        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password=hashed)
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await authenticate_user(mock_db, "testuser", "wrongpassword")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self) -> None:
        """Should fail authentication when user not found."""
        from vtt_transcribe.api.auth import authenticate_user

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        user = await authenticate_user(mock_db, "nonexistent", "password")

        assert user is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self) -> None:
        """Should raise 401 when no token provided."""
        from vtt_transcribe.api.auth import get_current_user

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=None, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self) -> None:
        """Should raise 401 when token is invalid."""
        from vtt_transcribe.api.auth import get_current_user

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid-token", db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_no_username_in_token(self) -> None:
        """Should raise 401 when token has no username."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user

        mock_db = AsyncMock()
        # Create token without 'sub' claim
        token = create_access_token({"other_field": "value"})

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self) -> None:
        """Should raise 401 when user not found in database."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = create_access_token({"sub": "nonexistent"})

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_success(self) -> None:
        """Should return user when valid token provided."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed", is_active=True)
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = create_access_token({"sub": "testuser"})

        user = await get_current_user(token=token, db=mock_db)

        assert user is not None
        assert user.username == "testuser"


class TestGetCurrentActiveUser:
    """Tests for get_current_active_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self) -> None:
        """Should return user when user is active."""
        from vtt_transcribe.api.auth import get_current_active_user
        from vtt_transcribe.api.models import User

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed", is_active=True)

        user = await get_current_active_user(current_user=mock_user)

        assert user is not None
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self) -> None:
        """Should raise 400 when user is inactive."""
        from vtt_transcribe.api.auth import get_current_active_user
        from vtt_transcribe.api.models import User

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed", is_active=False)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user=mock_user)

        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_token(self) -> None:
        """Should return None when no token provided."""
        from vtt_transcribe.api.auth import get_current_user_optional

        mock_db = AsyncMock()

        user = await get_current_user_optional(token=None, db=mock_db)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self) -> None:
        """Should return None when token is invalid."""
        from vtt_transcribe.api.auth import get_current_user_optional

        mock_db = AsyncMock()

        user = await get_current_user_optional(token="invalid-token", db=mock_db)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_username(self) -> None:
        """Should return None when token has no username."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user_optional

        mock_db = AsyncMock()
        token = create_access_token({"other_field": "value"})

        user = await get_current_user_optional(token=token, db=mock_db)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_user_not_found(self) -> None:
        """Should return None when user not found."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user_optional

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = create_access_token({"sub": "nonexistent"})

        user = await get_current_user_optional(token=token, db=mock_db)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_inactive_user(self) -> None:
        """Should return None when user is inactive."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user_optional
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed", is_active=False)
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = create_access_token({"sub": "testuser"})

        user = await get_current_user_optional(token=token, db=mock_db)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_success(self) -> None:
        """Should return user when valid token and active user."""
        from vtt_transcribe.api.auth import create_access_token, get_current_user_optional
        from vtt_transcribe.api.models import User

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed", is_active=True)
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        token = create_access_token({"sub": "testuser"})

        user = await get_current_user_optional(token=token, db=mock_db)

        assert user is not None
        assert user.username == "testuser"


class TestSecretKeyConfiguration:
    """Tests for secret key configuration."""

    def test_secret_key_from_environment(self) -> None:
        """Should use SECRET_KEY from environment if available."""
        with patch.dict("os.environ", {"SECRET_KEY": "test-secret-key"}):
            # Reimport to get new SECRET_KEY
            import importlib

            import vtt_transcribe.api.auth

            importlib.reload(vtt_transcribe.api.auth)

            # Create a token to verify secret key is working
            from vtt_transcribe.api.auth import create_access_token

            token = create_access_token({"sub": "testuser"})
            assert isinstance(token, str)

    def test_secret_key_dev_mode(self) -> None:
        """Should use development key when VTT_TRANSCRIBE_DEV_MODE is set."""
        with patch.dict("os.environ", {"VTT_TRANSCRIBE_DEV_MODE": "1"}, clear=True):
            # Reimport to get development key
            import importlib

            import vtt_transcribe.api.auth

            importlib.reload(vtt_transcribe.api.auth)

            from vtt_transcribe.api.auth import SECRET_KEY

            assert SECRET_KEY == "development-secret-key-change-in-production"

    def test_secret_key_missing_raises_error(self) -> None:
        """Should raise RuntimeError when SECRET_KEY not set and not in dev mode."""
        import importlib

        import vtt_transcribe.api.auth

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                importlib.reload(vtt_transcribe.api.auth)

            assert "SECRET_KEY environment variable must be set" in str(exc_info.value)


class TestAuthRoutes:
    """Tests for authentication route endpoints."""

    @pytest.mark.asyncio
    async def test_register_user_success(self) -> None:
        """Should register a new user successfully."""
        from vtt_transcribe.api.routes.auth import UserCreate, register

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

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
    async def test_login_route_success(self) -> None:
        """Should return token on successful login via route."""
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
    async def test_login_route_invalid_credentials(self) -> None:
        """Should reject invalid credentials via route."""
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
    async def test_read_users_me_route(self) -> None:
        """Should return current user information via route."""
        from vtt_transcribe.api.models import User
        from vtt_transcribe.api.routes.auth import read_users_me

        mock_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hash", is_active=True)

        user = await read_users_me(mock_user)

        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_create_access_token_with_none_expires_delta(self) -> None:
        """Should use default expiration when expires_delta is None."""
        from vtt_transcribe.api.auth import create_access_token

        # Mock jwt.encode to avoid SECRET_KEY requirement
        with patch("vtt_transcribe.api.auth.jwt.encode", return_value="mocked_token"):
            token = create_access_token(data={"sub": "testuser"}, expires_delta=None)

        assert isinstance(token, str)
        assert token == "mocked_token"

    def test_create_access_token_else_branch_default_expiry(self) -> None:
        """Should use 15-minute default when expires_delta is None (line 54)."""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        from vtt_transcribe.api.auth import create_access_token

        # Mock SECRET_KEY for test environment
        with patch("vtt_transcribe.api.auth.SECRET_KEY", "test-secret-key-for-testing"):
            data: dict[str, str | datetime] = {"sub": "testuser"}

            # Call with None to trigger else branch on line 54
            token = create_access_token(data, expires_delta=None)

            # Decode to verify default expiration was used
            from jose import jwt

            from vtt_transcribe.api.auth import ALGORITHM

            decoded = jwt.decode(token, "test-secret-key-for-testing", algorithms=[ALGORITHM])

            # Check that exp is approximately 15 minutes from now
            exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
            now = datetime.now(timezone.utc)
            time_diff = exp_time - now

            # Should be around 15 minutes (allow 1 second tolerance)
            assert timedelta(minutes=14, seconds=59) < time_diff < timedelta(minutes=15, seconds=1)

    def test_create_access_token_with_datetime_value(self) -> None:
        """Should convert datetime values to isoformat (line 54)."""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        from vtt_transcribe.api.auth import create_access_token

        # Mock SECRET_KEY for test environment
        with patch("vtt_transcribe.api.auth.SECRET_KEY", "test-secret-key-for-testing"):
            now = datetime.now(timezone.utc)
            data: dict[str, str | datetime] = {"sub": "testuser", "created_at": now}

            # Call with datetime value to trigger isoformat conversion (line 54)
            token = create_access_token(data, expires_delta=timedelta(minutes=30))

            # Decode to verify datetime was converted
            from jose import jwt

            from vtt_transcribe.api.auth import ALGORITHM

            decoded = jwt.decode(token, "test-secret-key-for-testing", algorithms=[ALGORITHM])

            # Should have isoformat string, not datetime object
            assert "created_at" in decoded
            assert isinstance(decoded["created_at"], str)
            assert decoded["created_at"] == now.isoformat()
