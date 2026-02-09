"""FastAPI application for VTT Transcribe."""

from fastapi import FastAPI

app = FastAPI(
    title="VTT Transcribe API",
    description="Transcribe video and audio files to text using OpenAI Whisper with optional speaker diarization",
    version="0.4.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
