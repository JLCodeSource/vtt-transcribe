"""FastAPI application for vtt-transcribe web service."""

from fastapi import FastAPI

app = FastAPI(title="vtt-transcribe API", version="0.4.0")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
