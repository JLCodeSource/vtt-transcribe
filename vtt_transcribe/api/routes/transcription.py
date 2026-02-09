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


@router.post("/transcribe")
async def create_transcription_job(
    file: UploadFile = File(...),  # noqa: B008
    api_key: str = Form(...),
) -> dict[str, str]:
    """Create a new transcription job."""
    if not file.filename:
        raise HTTPException(status_code=422, detail="File must have a filename")

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
    }

    task = asyncio.create_task(_process_transcription(job_id, file, api_key))
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


async def _process_transcription(job_id: str, file: UploadFile, api_key: str) -> None:
    """Process transcription job asynchronously."""
    try:
        jobs[job_id]["status"] = "processing"

        filename = file.filename or "audio.mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            content = await file.read()
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
