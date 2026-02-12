"""FastAPI application factory and configuration."""

import contextlib
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from vtt_transcribe import __version__
from vtt_transcribe.api.database import init_db
from vtt_transcribe.api.routes import api_keys, auth, health, jobs, oauth, transcription, websockets


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore
    """Lifespan event handler for database initialization."""
    # Startup: Initialize database tables
    with contextlib.suppress(Exception):
        # Database initialization failed, continue without DB functionality
        await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="vtt-transcribe API",
    version=__version__,
    description="REST API for transcribing audio and video files using OpenAI Whisper",
    lifespan=lifespan,
)

# Session middleware for OAuth state management (CSRF protection)
# Generate secure secret with: python -c "import secrets; print(secrets.token_hex(32))"
session_secret = os.getenv("SESSION_SECRET", os.urandom(32).hex())
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="vtt_session",
    max_age=3600,  # 1 hour
    same_site="lax",
    https_only=False,  # Set to True in production with HTTPS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(oauth.router)

# API routes (authentication handled per-endpoint via dependencies)
app.include_router(api_keys.router)
app.include_router(jobs.router)
app.include_router(transcription.router)
app.include_router(websockets.router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with welcome message."""
    return {
        "message": "Welcome to vtt-transcribe API",
        "version": __version__,
        "docs": "/docs",
        "websocket": "/ws/jobs/{job_id}",
    }
