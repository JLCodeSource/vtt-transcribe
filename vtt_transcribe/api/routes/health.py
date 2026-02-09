"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter

from vtt_transcribe import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}
