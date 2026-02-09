"""FastAPI application for VTT Transcribe."""

import uuid
from pathlib import Path
from tempfile import mkdtemp
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

# Maximum file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Supported file extensions
SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}

# Temporary upload directory
UPLOAD_DIR = Path(mkdtemp(prefix="vtt_transcribe_"))

app = FastAPI(
    title="VTT Transcribe API",
    description="Transcribe video and audio files to text using OpenAI Whisper with optional speaker diarization",
    version="0.4.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/v1/transcribe")
async def upload_file(
    file: Annotated[UploadFile, File(description="Audio or video file to transcribe")],
) -> dict[str, str]:
    """Upload audio/video file for transcription.

    Args:
        file: Uploaded audio or video file

    Returns:
        Job ID and status

    Raises:
        HTTPException: If file type is unsupported or file is too large
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes. Maximum size: {MAX_FILE_SIZE} bytes",
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Save file to temporary location
    upload_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    upload_path.write_bytes(content)

    return {
        "job_id": job_id,
        "status": "pending",
    }
