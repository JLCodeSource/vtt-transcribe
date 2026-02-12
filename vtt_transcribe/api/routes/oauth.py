"""OAuth provider authentication routes."""

import logging
import os
import secrets
from datetime import timedelta
from urllib.parse import urlparse

import httpx
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from vtt_transcribe.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
)
from vtt_transcribe.api.database import get_db
from vtt_transcribe.api.models import User

router = APIRouter(prefix="/oauth", tags=["oauth"])
logger = logging.getLogger(__name__)

# Initialize OAuth
oauth = OAuth()

# Configure OAuth providers
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Validate FRONTEND_URL
def validate_frontend_url(url: str) -> bool:
    """Validate that FRONTEND_URL is a properly formatted URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


if not validate_frontend_url(FRONTEND_URL):
    logger.warning(f"FRONTEND_URL '{FRONTEND_URL}' is not a valid URL format")

# Google OAuth
if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# GitHub OAuth
if os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"):
    oauth.register(
        name="github",
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        authorize_url="https://github.com/login/oauth/authorize",
        authorize_params=None,
        access_token_url="https://github.com/login/oauth/access_token",  # noqa: S106
        access_token_params=None,
        client_kwargs={"scope": "user:email"},
    )

# Microsoft OAuth
if os.getenv("MICROSOFT_CLIENT_ID") and os.getenv("MICROSOFT_CLIENT_SECRET"):
    oauth.register(
        name="microsoft",
        client_id=os.getenv("MICROSOFT_CLIENT_ID"),
        client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@router.get("/providers")
async def get_providers() -> dict[str, list[str]]:
    """Get list of enabled OAuth providers (only those with both CLIENT_ID and CLIENT_SECRET)."""
    providers = []
    if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
        providers.append("google")
    if os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"):
        providers.append("github")
    if os.getenv("MICROSOFT_CLIENT_ID") and os.getenv("MICROSOFT_CLIENT_SECRET"):
        providers.append("microsoft")
    return {"providers": providers}


@router.get("/login/{provider}")
async def oauth_login(provider: str, request: Request) -> RedirectResponse:
    """Initiate OAuth login with provider."""
    if provider not in ["google", "github", "microsoft"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider")

    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} OAuth not configured",
        )

    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, str(redirect_uri))  # type: ignore[no-any-return]


async def get_user_info_from_google(token: dict) -> str | None:
    """Extract email from Google OAuth token."""
    user_info = token.get("userinfo")
    return user_info.get("email") if user_info else None


async def get_user_info_from_github(client, token: dict) -> str | None:
    """Fetch email from GitHub API (handles private emails)."""
    try:
        # Get user data
        user_response = await client.get("https://api.github.com/user", token=token)
        if user_response.status_code not in (200, 201):
            logger.warning(f"GitHub user API returned status {user_response.status_code}")
            return None

        user_data = user_response.json()
        if not isinstance(user_data, dict):
            logger.warning("GitHub user API returned non-dict response")
            return None

        email = user_data.get("email")

        # If email is private, fetch from emails endpoint
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                token=token,
            )
            if emails_response.status_code not in (200, 201):
                logger.warning(f"GitHub emails API returned status {emails_response.status_code}")
                return None

            emails = emails_response.json()
            if not isinstance(emails, list):
                logger.warning("GitHub emails API returned non-list response")
                return None

            primary_email = next(
                (e for e in emails if isinstance(e, dict) and e.get("primary")),
                None,
            )
            email = primary_email.get("email") if primary_email else None

        return email
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching GitHub user info: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching GitHub user info: {e}")
        return None


async def get_user_info_from_microsoft(token: dict) -> str | None:
    """Extract email from Microsoft OAuth token."""
    user_info = token.get("userinfo")
    return user_info.get("email") if user_info else None


async def generate_unique_username(
    db: AsyncSession,
    base_username: str,
    provider: str,
    max_attempts: int = 100,
) -> str | None:
    """
    Generate a unique username with format oauth-{provider}-{base}.
    
    Returns None if unable to generate unique username after max_attempts.
    """
    # Use OAuth-specific prefix to avoid confusion with regular users
    username = f"oauth-{provider}-{base_username}"
    counter = 1

    for _ in range(max_attempts):
        existing_user = await get_user_by_username(db, username)
        if not existing_user:
            return username
        # Add random suffix for uniqueness
        username = f"oauth-{provider}-{base_username}-{secrets.token_hex(4)}"
        counter += 1

    logger.error(f"Failed to generate unique username after {max_attempts} attempts")
    return None


async def get_or_create_oauth_user(
    db: AsyncSession,
    email: str,
    provider: str,
) -> User | None:
    """
    Get existing user or create new OAuth user.
    
    Only allows OAuth login for users originally created via OAuth to prevent account takeover.
    """
    user = await get_user_by_email(db, email)

    if user:
        # Security: Only allow OAuth login if user was created via OAuth
        if user.oauth_provider is None:
            logger.warning(
                f"Attempted OAuth login for non-OAuth user: {email} via {provider}"
            )
            return None
        # User exists and was created via OAuth - allow login
        return user

    # Create new OAuth user
    local_part = email.split("@", 1)[0]
    username = await generate_unique_username(db, local_part, provider)
    
    if not username:
        logger.error(f"Could not generate unique username for {email}")
        return None

    user = User(
        username=username,
        email=email,
        # Random password for OAuth users (they can only log in via OAuth)
        hashed_password=get_password_hash(secrets.token_hex(32)),
        is_active=True,
        is_superuser=False,
        oauth_provider=provider,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# User-friendly error messages
ERROR_MESSAGES = {
    "oauth_failed": "Authentication failed. Please try again or use a different login method.",
    "no_email": "We couldn't retrieve your email address. Please ensure your email is visible in your provider settings and try again.",
    "invalid_provider": "Invalid authentication provider. Please use one of the supported providers.",
    "username_unavailable": "Unable to create your account. Please contact support for assistance.",
    "account_mismatch": "This email is already registered with a different login method. Please use your original login method.",
}


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle OAuth callback from provider."""
    if provider not in ["google", "github", "microsoft"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider")

    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} OAuth not configured",
        )

    # Authorize access token with specific error handling
    try:
        token = await client.authorize_access_token(request)
    except OAuthError as e:
        logger.error(f"OAuth authorization error for {provider}: {e.error} - {e.description}")
        return RedirectResponse(url=f"{FRONTEND_URL}#error=oauth_failed")
    except Exception as e:
        logger.error(f"Unexpected error during OAuth authorization for {provider}: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}#error=oauth_failed")

    # Get user info from provider
    email: str | None = None
    if provider == "google":
        email = await get_user_info_from_google(token)
    elif provider == "github":
        email = await get_user_info_from_github(client, token)
    elif provider == "microsoft":
        email = await get_user_info_from_microsoft(token)
    else:
        return RedirectResponse(url=f"{FRONTEND_URL}#error=invalid_provider")

    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}#error=no_email")

    # Find or create user
    user = await get_or_create_oauth_user(db, email, provider)
    
    if not user:
        # This happens when a non-OAuth user tries to log in via OAuth
        return RedirectResponse(url=f"{FRONTEND_URL}#error=account_mismatch")

    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    # Redirect to frontend with token in URL fragment (more secure than query params)
    return RedirectResponse(url=f"{FRONTEND_URL}#token={access_token}&username={user.username}")
