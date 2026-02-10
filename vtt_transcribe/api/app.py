"""FastAPI application factory and configuration."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vtt_transcribe import __version__
from vtt_transcribe.api.database import init_db
from vtt_transcribe.api.routes import api_keys, auth, health, jobs, transcription, websockets


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore
    """Lifespan event handler for database initialization."""
    # Startup: Initialize database tables
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="vtt-transcribe API",
    version=__version__,
    description="REST API for transcribing audio and video files using OpenAI Whisper",
    lifespan=lifespan,
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

# Protected routes (require authentication)
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
