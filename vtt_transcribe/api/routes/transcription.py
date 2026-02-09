"""Transcription API endpoints."""

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from vtt_transcribe.transcriber import VideoTranscriber

router = APIRouter(tags=["transcription"])

jobs: dict[str, dict[str, Any]] = {}

# Maximum file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Supported file extensions
SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".mpeg", ".mpga", ".webm"}


@router.post("/transcribe")
async def create_transcription_job(
    file: UploadFile = File(...),  # noqa: B008
    api_key: str = Form(...),
) -> dict[str, str]:
    """Create a new transcription job.

    Args:
        file: Audio or video file to transcribe
        api_key: OpenAI API key

    Returns:
        Job ID and status

    Raises:
        HTTPException: If validation fails
    """
    # Validate filename exists
    if not file.filename:
        raise HTTPException(status_code=422, detail="File must have a filename")

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
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes. Maximum size: {MAX_FILE_SIZE} bytes ({max_mb}MB)",
        )

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "file_size": len(content),
    }

    # Store content for processing
    task = asyncio.create_task(_process_transcription(job_id, content, file.filename or "audio.mp3", api_key))
    _ = task

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Transcription job created",
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get status of a transcription job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


async def _process_transcription(job_id: str, content: bytes, filename: str, api_key: str) -> None:
    """Process transcription job asynchronously.

    Args:
        job_id: Unique job identifier
        content: File content bytes
        filename: Original filename
        api_key: OpenAI API key
    """
    try:
        jobs[job_id]["status"] = "processing"

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            transcriber = VideoTranscriber(api_key)
            result = await asyncio.to_thread(transcriber.transcribe, tmp_path)

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result

        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
