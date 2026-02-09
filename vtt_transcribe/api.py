"""FastAPI application for vtt-transcribe web service."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="vtt-transcribe API", version="0.4.0")

# In-memory job storage (will be replaced with database later)
jobs: dict[str, dict[str, Any]] = {}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/transcribe", status_code=202)
async def create_transcription_job(
    file: UploadFile = File(...),  # noqa: B008
) -> dict[str, str]:
    """
    Upload a file for transcription.

    Returns a job ID that can be used to check status.
    """
    job_id = str(uuid.uuid4())

    # Store job metadata
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "content_type": file.content_type,
        "created_at": datetime.now(UTC).isoformat(),
    }

    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a transcription job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]
