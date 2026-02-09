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
    diarize: bool = Form(False),  # noqa: FBT001, FBT003
    hf_token: str | None = Form(None),
    device: str | None = Form(None),
) -> dict[str, str]:
    """Create a new transcription job.

    Args:
        file: Audio or video file
        api_key: OpenAI API key
        diarize: Enable speaker diarization
        hf_token: HuggingFace token (required if diarize=True)
        device: Device for diarization (auto/cpu/cuda)

    Returns:
        Job ID and status
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="File must have a filename")

    if diarize and not hf_token:
        raise HTTPException(
            status_code=400,
            detail="HuggingFace token required for diarization. Provide hf_token parameter.",
        )

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
        "diarize": diarize,
        "hf_token": hf_token if diarize else None,
        "device": device if diarize else None,
    }

    task = asyncio.create_task(
        _process_transcription(job_id, content, file.filename or "audio.mp3", api_key, diarize, hf_token, device)
    )
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


@router.post("/diarize")
async def create_diarization_job(
    file: UploadFile = File(...),  # noqa: B008
    hf_token: str = Form(...),
    device: str | None = Form(None),
) -> dict[str, str]:
    """Create a diarization-only job.

    Args:
        file: Audio or video file
        hf_token: HuggingFace token for diarization
        device: Device for diarization (auto/cpu/cuda)

    Returns:
        Job ID and status
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="File must have a filename")

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "diarize_only": True,
        "hf_token": hf_token,
        "device": device,
    }

    task = asyncio.create_task(_process_diarization(job_id, file, hf_token, device))
    _ = task

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Diarization job created",
    }


async def _process_diarization(job_id: str, file: UploadFile, _hf_token: str, _device: str | None = None) -> None:
    """Process diarization-only job asynchronously."""
    # Note: hf_token and device will be used when integrating pyannote.audio
    try:
        jobs[job_id]["status"] = "processing"

        filename = file.filename or "audio.mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            # Note: Actual diarization logic would go here
            # For now, placeholder result
            result = f"Diarization result for {filename}"

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result

        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


async def _process_transcription(
    job_id: str,
    content: bytes,
    filename: str,
    api_key: str,
    _diarize: bool = False,  # noqa: FBT001, FBT002
    _hf_token: str | None = None,
    _device: str | None = None,
) -> None:
    """Process transcription job asynchronously."""
    # Note: diarize, hf_token, device will be used when integrating diarization
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
