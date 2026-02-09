"""FastAPI application for VTT Transcribe."""

import contextlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import mkdtemp
from typing import Annotated, Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from vtt_transcribe.transcriber import VideoTranscriber

# Maximum file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Supported file extensions
SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}

# Temporary upload directory
UPLOAD_DIR = Path(mkdtemp(prefix="vtt_transcribe_"))

# In-memory job storage (will be replaced with database)
jobs: dict[str, dict[str, Any]] = {}

app = FastAPI(
    title="VTT Transcribe API",
    description="Transcribe video and audio files to text using OpenAI Whisper with optional speaker diarization",
    version="0.4.0",
)


async def process_transcription(job_id: str, file_path: Path, api_key: str) -> None:
    """Background task to process transcription."""
    try:
        jobs[job_id]["status"] = "processing"

        # Transcribe the file
        transcriber = VideoTranscriber(api_key)
        transcript_text = transcriber.transcribe(file_path, keep_audio=False)

        # Update job with results
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["transcript"] = {"text": transcript_text}
        jobs[job_id]["completed_at"] = datetime.now(UTC).isoformat()

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["failed_at"] = datetime.now(UTC).isoformat()

    finally:
        # Clean up temporary file
        with contextlib.suppress(Exception):
            file_path.unlink(missing_ok=True)  # noqa: ASYNC240


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/v1/transcribe")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="Audio or video file to transcribe")],
    api_key: str | None = Form(None),
) -> dict[str, str]:
    """Upload audio/video file for transcription.

    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded audio or video file
        api_key: Optional OpenAI API key for background transcription

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

    # Store job metadata
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "created_at": datetime.now(UTC).isoformat(),
    }

    # If API key provided, queue background transcription
    if api_key:
        background_tasks.add_task(process_transcription, job_id, upload_path, api_key)

    return {
        "job_id": job_id,
        "status": "pending",
    }


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a transcription job.

    Args:
        job_id: The unique job identifier

    Returns:
        Job status and metadata

    Raises:
        HTTPException: If job not found
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]
