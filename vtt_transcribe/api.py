"""FastAPI application for vtt-transcribe web service."""

import contextlib
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from vtt_transcribe.transcriber import VideoTranscriber

app = FastAPI(title="vtt-transcribe API", version="0.4.0")

# In-memory job storage (will be replaced with database later)
jobs: dict[str, dict[str, Any]] = {}


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
        # Clean up temporary file (sync operations in async function)
        with contextlib.suppress(Exception):
            file_path.unlink(missing_ok=True)  # noqa: ASYNC240


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/transcribe", status_code=202)
async def create_transcription_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    api_key: str = Form(...),
) -> dict[str, str]:
    """
    Upload a file for transcription.

    Returns a job ID that can be used to check status.
    """
    job_id = str(uuid.uuid4())

    # Save uploaded file to temporary location using NamedTemporaryFile
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=Path(file.filename or "audio.mp3").suffix,
    ) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    # Store job metadata
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "content_type": file.content_type,
        "created_at": datetime.now(UTC).isoformat(),
    }

    # Queue background task
    background_tasks.add_task(process_transcription, job_id, temp_path, api_key)

    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a transcription job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]
