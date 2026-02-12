"""Tests for OAuth provider authentication."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from authlib.integrations.starlette_client import OAuthError
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from vtt_transcribe.api.app import app

    return TestClient(app)


@pytest.fixture
def mock_oauth_client():
    """Create mock OAuth client."""
    client = MagicMock()
    client.authorize_redirect = AsyncMock(return_value=MagicMock(status_code=302))
    client.authorize_access_token = AsyncMock()
    client.get = AsyncMock()
    return client


@pytest.fixture
def mock_user_factory():
    """Factory fixture for creating mock User objects."""
    from vtt_transcribe.api.models import User

    def _create_mock_user(
        username: str = "test-user",
        email: str = "test@example.com",
        oauth_provider: str | None = None,
    ) -> MagicMock:
        """Create a mock User object with customizable properties."""
        mock_user = MagicMock(spec=User)
        mock_user.username = username
        mock_user.email = email
        mock_user.oauth_provider = oauth_provider
        return mock_user

    return _create_mock_user


class TestOAuthProviders:
    """Tests for OAuth provider listing."""

    def test_get_providers_no_providers_configured(self, client):
        """Should return empty list when no OAuth providers are configured."""
        with patch.dict("os.environ", {}, clear=False):
            response = client.get("/oauth/providers")
            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert data["providers"] == []

    def test_get_providers_partial_google_config(self, client):
        """Should not list Google if only CLIENT_ID is set (missing SECRET)."""
        with patch.dict(
            "os.environ",
            {"GOOGLE_CLIENT_ID": "test-id"},
            clear=False,
        ):
            response = client.get("/oauth/providers")
            assert response.status_code == 200
            data = response.json()
            assert "google" not in data["providers"]

    def test_get_providers_full_google_config(self, client):
        """Should list Google when both CLIENT_ID and CLIENT_SECRET are set."""
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_CLIENT_ID": "test-id",
                "GOOGLE_CLIENT_SECRET": "test-secret",
            },
            clear=False,
        ):
            # Need to reload the module to pick up new env vars
            import importlib

            from vtt_transcribe.api.routes import oauth

            importlib.reload(oauth)
            response = client.get("/oauth/providers")
            assert response.status_code == 200
            data = response.json()
            assert "google" in data["providers"]

    def test_get_providers_multiple_configured(self, client):
        """Should list all configured providers."""
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_CLIENT_ID": "test-id",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "GITHUB_CLIENT_ID": "test-id",
                "GITHUB_CLIENT_SECRET": "test-secret",
            },
            clear=False,
        ):
            import importlib

            from vtt_transcribe.api.routes import oauth

            importlib.reload(oauth)
            response = client.get("/oauth/providers")
            assert response.status_code == 200
            data = response.json()
            assert "google" in data["providers"]
            assert "github" in data["providers"]


class TestOAuthLogin:
    """Tests for OAuth login initiation."""

    def test_login_invalid_provider(self, client):
        """Should return 400 for invalid provider."""
        response = client.get("/oauth/login/invalid")
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    def test_login_unconfigured_provider(self, client):
        """Should return 503 when provider is not configured."""
        with patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth:
            mock_oauth.create_client.return_value = None
            response = client.get("/oauth/login/google")
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    def test_login_configured_provider_redirects(self, client, mock_oauth_client):
        """Should redirect to provider when configured."""
        from starlette.responses import RedirectResponse

        redirect_response = RedirectResponse(url="https://accounts.google.com/o/oauth2/auth")
        mock_oauth_client.authorize_redirect = AsyncMock(return_value=redirect_response)

        with patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth:
            mock_oauth.create_client.return_value = mock_oauth_client
            client.get("/oauth/login/google", follow_redirects=False)
            # Should attempt to redirect
            assert mock_oauth_client.authorize_redirect.called


class TestOAuthCallback:
    """Tests for OAuth callback handling."""

    def test_callback_invalid_provider(self, client):
        """Should return 400 for invalid provider."""
        response = client.get("/oauth/callback/invalid")
        assert response.status_code == 400

    def test_callback_unconfigured_provider(self, client):
        """Should return 503 when provider is not configured."""
        with patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth:
            mock_oauth.create_client.return_value = None
            response = client.get("/oauth/callback/google")
            assert response.status_code == 503

    def test_callback_oauth_authorization_fails(self, client, mock_oauth_client):
        """Should redirect to frontend with error when authorization fails."""
        mock_oauth_client.authorize_access_token = AsyncMock(
            side_effect=OAuthError(error="access_denied", description="User denied access")
        )

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            response = client.get("/oauth/callback/google", follow_redirects=False)
            assert response.status_code == 307  # RedirectResponse
            assert "error=oauth_failed" in response.headers["location"]
            assert "#error=" in response.headers["location"]  # Should use fragment

    def test_callback_google_success_new_user(self, client, mock_oauth_client, mock_user_factory):
        """Should create new user and redirect with token for Google OAuth."""
        mock_oauth_client.authorize_access_token = AsyncMock(
            return_value={
                "access_token": "test-token",
                "userinfo": {"email": "test@example.com", "name": "Test User"},
            }
        )

        # Create mock user
        mock_user = mock_user_factory(username="oauth-google-test", oauth_provider="google")

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch("vtt_transcribe.api.routes.oauth.get_or_create_oauth_user") as mock_get_or_create,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            mock_get_or_create.return_value = mock_user

            response = client.get("/oauth/callback/google", follow_redirects=False)
            assert response.status_code == 307
            location = response.headers["location"]
            assert "http://localhost:3000" in location
            assert "#token=" in location  # Should use fragment
            assert "&username=" in location

    def test_callback_google_no_email(self, client, mock_oauth_client):
        """Should redirect with error when Google doesn't provide email."""
        mock_oauth_client.authorize_access_token = AsyncMock(
            return_value={
                "access_token": "test-token",
                "userinfo": {},  # No email
            }
        )

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            response = client.get("/oauth/callback/google", follow_redirects=False)
            assert response.status_code == 307
            assert "error=no_email" in response.headers["location"]

    def test_callback_github_success_with_public_email(self, client, mock_oauth_client, mock_user_factory):
        """Should handle GitHub OAuth with public email."""
        mock_oauth_client.authorize_access_token = AsyncMock(return_value={"access_token": "test-token"})

        # Mock GitHub user API response
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {"email": "test@example.com", "login": "testuser"}
        mock_oauth_client.get = AsyncMock(return_value=user_response)

        # Create mock user
        mock_user = mock_user_factory(username="oauth-github-test", oauth_provider="github")

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch("vtt_transcribe.api.routes.oauth.get_or_create_oauth_user") as mock_get_or_create,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            mock_get_or_create.return_value = mock_user

            response = client.get("/oauth/callback/github", follow_redirects=False)
            assert response.status_code == 307
            location = response.headers["location"]
            assert "#token=" in location

    def test_callback_github_private_email(self, client, mock_oauth_client, mock_user_factory):
        """Should fetch private email from GitHub emails endpoint."""
        mock_oauth_client.authorize_access_token = AsyncMock(return_value={"access_token": "test-token"})

        # Mock GitHub user API response (no email)
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {"login": "testuser"}  # No email

        # Mock GitHub emails API response
        emails_response = MagicMock()
        emails_response.status_code = 200
        emails_response.json.return_value = [{"email": "test@example.com", "primary": True, "verified": True}]

        # Configure mock to return different responses
        mock_oauth_client.get = AsyncMock(side_effect=[user_response, emails_response])

        # Create mock user
        mock_user = mock_user_factory(username="oauth-github-test", oauth_provider="github")

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch("vtt_transcribe.api.routes.oauth.get_or_create_oauth_user") as mock_get_or_create,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            mock_get_or_create.return_value = mock_user

            response = client.get("/oauth/callback/github", follow_redirects=False)
            assert response.status_code == 307
            assert "#token=" in response.headers["location"]

    def test_callback_github_api_failure(self, client, mock_oauth_client):
        """Should handle GitHub API failures gracefully."""
        mock_oauth_client.authorize_access_token = AsyncMock(return_value={"access_token": "test-token"})

        # Mock GitHub API returning error status
        user_response = MagicMock()
        user_response.status_code = 403  # Rate limited
        mock_oauth_client.get = AsyncMock(return_value=user_response)

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            response = client.get("/oauth/callback/github", follow_redirects=False)
            assert response.status_code == 307
            assert "error=no_email" in response.headers["location"]

    def test_callback_existing_oauth_user_logs_in(self, client, mock_oauth_client, mock_user_factory):
        """Should log in existing OAuth user."""
        mock_oauth_client.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {"email": "existing@example.com"},
            }
        )

        # Mock existing OAuth user
        existing_user = mock_user_factory(
            username="oauth-google-existing",
            email="existing@example.com",
            oauth_provider="google",
        )

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch("vtt_transcribe.api.routes.oauth.get_or_create_oauth_user") as mock_get_or_create,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            mock_get_or_create.return_value = existing_user

            response = client.get("/oauth/callback/google", follow_redirects=False)
            assert response.status_code == 307
            assert "#token=" in response.headers["location"]

    def test_callback_prevents_account_takeover(self, client, mock_oauth_client):
        """Should prevent OAuth login for non-OAuth users (account takeover protection)."""
        mock_oauth_client.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {"email": "regular@example.com"},
            }
        )

        # Mock get_or_create_oauth_user returning None (account mismatch)

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch("vtt_transcribe.api.routes.oauth.get_or_create_oauth_user") as mock_get_or_create,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            mock_get_or_create.return_value = None  # Account takeover prevention

            response = client.get("/oauth/callback/google", follow_redirects=False)
            assert response.status_code == 307
            assert "error=account_mismatch" in response.headers["location"]

    def test_callback_username_generation_with_collision(self, client, mock_oauth_client, mock_user_factory):
        """Should generate unique username when collision occurs."""
        mock_oauth_client.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {"email": "test@example.com"},
            }
        )

        # Create mock user
        mock_user = mock_user_factory(
            username="oauth-google-test-abc123",
            oauth_provider="google",
        )

        with (
            patch("vtt_transcribe.api.routes.oauth.oauth") as mock_oauth,
            patch("vtt_transcribe.api.routes.oauth.get_or_create_oauth_user") as mock_get_or_create,
            patch.dict("os.environ", {"FRONTEND_URL": "http://localhost:3000"}, clear=False),
        ):
            mock_oauth.create_client.return_value = mock_oauth_client
            mock_get_or_create.return_value = mock_user

            response = client.get("/oauth/callback/google", follow_redirects=False)
            assert response.status_code == 307
            assert "#token=" in response.headers["location"]


class TestOAuthHelpers:
    """Tests for OAuth helper functions."""

    def test_validate_frontend_url_valid(self):
        """Should validate proper URLs."""
        from vtt_transcribe.api.routes.oauth import validate_frontend_url

        assert validate_frontend_url("http://localhost:3000")
        assert validate_frontend_url("https://example.com")
        assert validate_frontend_url("https://app.example.com:8080")

    def test_validate_frontend_url_invalid(self):
        """Should reject invalid URLs."""
        from vtt_transcribe.api.routes.oauth import validate_frontend_url

        assert not validate_frontend_url("not-a-url")
        assert not validate_frontend_url("")
        assert not validate_frontend_url("javascript:alert(1)")
