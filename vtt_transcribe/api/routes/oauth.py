"""OAuth provider authentication routes."""

import os

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from vtt_transcribe.api.auth import (
    create_access_token,
    get_password_hash,
    get_user_by_email,
)
from vtt_transcribe.api.database import get_db
from vtt_transcribe.api.models import User

router = APIRouter(prefix="/oauth", tags=["oauth"])

# Initialize OAuth
oauth = OAuth()

# Configure OAuth providers
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

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
    """Get list of enabled OAuth providers."""
    providers = []
    if os.getenv("GOOGLE_CLIENT_ID"):
        providers.append("google")
    if os.getenv("GITHUB_CLIENT_ID"):
        providers.append("github")
    if os.getenv("MICROSOFT_CLIENT_ID"):
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


@router.get("/callback/{provider}")
async def oauth_callback(  # noqa: C901
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

    try:
        token = await client.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=oauth_failed")

    # Get user info from provider
    email: str | None = None
    if provider == "google":
        user_info = token.get("userinfo")
        email = user_info.get("email") if user_info else None
    elif provider == "github":
        # GitHub needs an extra request for user info
        user_response = await client.get("https://api.github.com/user", token=token)
        user_data = user_response.json()
        email = user_data.get("email")

        # If email is private, fetch from emails endpoint
        if not email:
            emails_response = await client.get("https://api.github.com/user/emails", token=token)
            emails = emails_response.json()
            primary_email = next((e for e in emails if e.get("primary")), None)
            email = primary_email.get("email") if primary_email else None
    elif provider == "microsoft":
        user_info = token.get("userinfo")
        email = user_info.get("email") if user_info else None
    else:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=invalid_provider")

    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_email")

    # Find or create user
    user = await get_user_by_email(db, email)

    if not user:
        # Create new user from OAuth
        username = email.split("@")[0] + f"_{provider}"
        # Ensure unique username
        counter = 1
        base_username = username
        from vtt_transcribe.api.auth import get_user_by_username

        while await get_user_by_username(db, username):
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            # Random password for OAuth users
            hashed_password=get_password_hash(os.urandom(32).hex()),
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create JWT token
    from datetime import timedelta

    from vtt_transcribe.api.auth import ACCESS_TOKEN_EXPIRE_MINUTES

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    # Redirect to frontend with token
    return RedirectResponse(url=f"{FRONTEND_URL}?token={access_token}&username={user.username}")
