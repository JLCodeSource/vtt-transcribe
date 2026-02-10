"""User API key management routes."""

import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vtt_transcribe.api.auth import get_current_active_user
from vtt_transcribe.api.database import get_db
from vtt_transcribe.api.models import APIKey, User

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

# Encryption key for API keys (must be set via environment variable)
encryption_key_str = os.getenv("ENCRYPTION_KEY")
if encryption_key_str is None:
    msg = (
        "ENCRYPTION_KEY environment variable is not set. "
        "It must be configured to enable API key encryption/decryption. "
        'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )
    raise RuntimeError(msg)

ENCRYPTION_KEY = encryption_key_str.encode()
cipher = Fernet(ENCRYPTION_KEY)


# Request/Response models
class APIKeyCreate(BaseModel):
    """Create API key request."""

    service: str  # 'openai' or 'huggingface'
    api_key: str
    key_name: str | None = None


class APIKeyResponse(BaseModel):
    """API key response (encrypted key not exposed)."""

    model_config = {"from_attributes": True}

    id: int
    service: str
    key_name: str | None
    created_at: datetime
    last_used_at: datetime | None


def encrypt_key(key: str) -> str:
    """Encrypt an API key."""
    return cipher.encrypt(key.encode()).decode()


def decrypt_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    return cipher.decrypt(encrypted_key.encode()).decode()


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """Store an encrypted API key for external services."""
    # Validate service type
    valid_services = ["openai", "huggingface"]
    if key_data.service not in valid_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid service. Must be one of: {', '.join(valid_services)}",
        )

    # Encrypt the API key
    encrypted_key = encrypt_key(key_data.api_key)

    # Create new API key record
    new_key = APIKey(
        user_id=current_user.id,
        service=key_data.service,
        encrypted_key=encrypted_key,
        key_name=key_data.key_name,
    )

    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    return new_key


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[APIKey]:
    """List all API keys for the current user."""
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """Get a specific API key."""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id))
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an API key."""
    # Check if key exists and belongs to user
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id))
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    await db.execute(delete(APIKey).where(APIKey.id == key_id))
    await db.commit()


async def get_user_api_key(user_id: int, service: str, db: AsyncSession) -> str | None:
    """Get decrypted API key for a user and service."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user_id, APIKey.service == service).order_by(APIKey.created_at.desc())
    )
    key = result.scalar_one_or_none()

    if not key:
        return None

    # Update last used timestamp
    key.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    return decrypt_key(key.encrypted_key)
