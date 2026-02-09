"""FastAPI application factory and configuration."""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vtt_transcribe import __version__
from vtt_transcribe.api.routes import health, transcription

app = FastAPI(
    title="vtt-transcribe API",
    version=__version__,
    description="REST API for transcribing audio and video files using OpenAI Whisper",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(transcription.router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with welcome message."""
    return {
        "message": "Welcome to vtt-transcribe API",
        "version": __version__,
        "docs": "/docs",
    }
