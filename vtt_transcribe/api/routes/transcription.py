"""Transcription API endpoints."""

import asyncio
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse

from vtt_transcribe.logging_config import get_logger
from vtt_transcribe.transcriber import VideoTranscriber
from vtt_transcribe.translator import AudioTranslator

router = APIRouter(tags=["transcription"])
logger = get_logger(__name__)

# Jobs dictionary now includes progress_updates queue for each job
jobs: dict[str, dict[str, Any]] = {}


def _emit_progress(job_id: str, message: str, progress_type: str = "info") -> None:
    """Emit a progress update for a job.

    Args:
        job_id: Job identifier
        message: Progress message
        progress_type: Type of progress update (info, chunk, diarization, language, translation)
    """
    if job_id in jobs and "progress_updates" in jobs[job_id]:
        update = {
            "type": progress_type,
            "message": message,
            "timestamp": time.time(),
        }
        try:
            jobs[job_id]["progress_updates"].put_nowait(update)
        except asyncio.QueueFull:
            # Log but don't fail if queue is full - oldest events will be consumed first
            logger.warning(
                "Progress queue full for job - dropping event",
                extra={"job_id": job_id, "progress_message": message, "progress_type": progress_type},
            )
        except Exception as exc:
            # Log but don't fail if progress update cannot be enqueued for other reasons
            logger.warning(
                "Failed to enqueue progress update for job",
                extra={
                    "job_id": job_id,
                    "progress_message": message,
                    "error": repr(exc),
                },
            )


# Maximum file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Maximum progress queue size (to prevent unbounded memory growth)
# A typical transcription job emits ~10-20 progress events, so 100 is generous
MAX_PROGRESS_QUEUE_SIZE = 100

# Supported file extensions
SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".mpeg", ".mpga", ".webm"}


@router.post("/transcribe")
async def create_transcription_job(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    diarize: bool = Form(False),  # noqa: FBT001, FBT003
    hf_token: str | None = Form(None),
    device: str | None = Form(None),
    translate_to: str | None = Form(None),
) -> dict[str, str]:
    """Create a new transcription job.

    Args:
        file: Audio or video file
        api_key: OpenAI API key
        diarize: Enable speaker diarization
        hf_token: HuggingFace token (required if diarize=True)
        device: Device for diarization (auto/cpu/cuda)
        translate_to: Optional target language for translation (e.g., "Spanish", "French")

    Returns:
        Job ID and status
    """
    logger.info(
        "Creating transcription job",
        extra={
            "file_name": file.filename,
            "diarize": diarize,
            "has_hf_token": bool(hf_token),
            "device": device,
            "translate_to": translate_to,
        },
    )

    if not file.filename:
        logger.warning("Job creation failed: missing filename")
        raise HTTPException(status_code=422, detail="File must have a filename")

    if diarize and not hf_token:
        logger.warning(
            "Job creation failed: diarization requested without HF token",
            extra={"file_name": file.filename},
        )
        raise HTTPException(
            status_code=400,
            detail="HuggingFace token required for diarization. Provide hf_token parameter.",
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        logger.warning(
            "Job creation failed: unsupported file type",
            extra={"file_name": file.filename, "extension": file_ext},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        logger.warning(
            "Job creation failed: file too large",
            extra={
                "file_name": file.filename,
                "file_size_bytes": len(content),
                "max_size_bytes": MAX_FILE_SIZE,
            },
        )
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes. Maximum size: {MAX_FILE_SIZE} bytes ({max_mb}MB)",
        )

    job_id = str(uuid.uuid4())

    logger.info(
        "Transcription job created successfully",
        extra={
            "job_id": job_id,
            "file_name": file.filename,
            "file_size_mb": round(len(content) / (1024 * 1024), 2),
        },
    )

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "file_size": len(content),
        "diarize": diarize,
        "hf_token": hf_token if diarize else None,
        "device": device if diarize else None,
        "translate_to": translate_to,
        "progress_updates": asyncio.Queue(maxsize=MAX_PROGRESS_QUEUE_SIZE),  # Bounded queue for progress updates
    }

    task = asyncio.create_task(
        _process_transcription(job_id, content, file.filename or "audio.mp3", api_key, diarize, hf_token, device, translate_to)
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

    # Return job data excluding progress_updates queue (not JSON serializable)
    return {k: v for k, v in jobs[job_id].items() if k != "progress_updates"}


@router.post("/detect-language")
async def detect_language(
    file: UploadFile = File(...),
    api_key: str = Form(...),
) -> dict[str, str]:
    """Detect language of audio file.

    Args:
        file: Audio or video file
        api_key: OpenAI API key

    Returns:
        Detected language code and original filename
    """
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

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            transcriber = VideoTranscriber(api_key)
            language_code = await asyncio.to_thread(transcriber.detect_language, tmp_path)

            return {
                "language_code": language_code,
                "filename": file.filename,
            }

        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Language detection failed: {e!s}") from e


@router.post("/translate")
async def translate_transcript(
    transcript: str = Form(...),
    target_language: str = Form(...),
    api_key: str = Form(...),
    preserve_timestamps: bool = Form(True),  # noqa: FBT001, FBT003
) -> dict[str, str]:
    """Translate a transcript to target language.

    Args:
        transcript: Original transcript text
        target_language: Target language name (e.g., "Spanish", "French")
        api_key: OpenAI API key
        preserve_timestamps: If True, preserve timestamp format in output

    Returns:
        Translated transcript
    """
    try:
        translator = AudioTranslator(api_key)
        translated = await asyncio.to_thread(
            translator.translate_transcript, transcript, target_language, preserve_timestamps=preserve_timestamps
        )

        return {
            "original": transcript,
            "translated": translated,
            "target_language": target_language,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e!s}") from e


@router.post("/diarize")
async def create_diarization_job(
    file: UploadFile = File(...),
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
        "progress_updates": asyncio.Queue(maxsize=MAX_PROGRESS_QUEUE_SIZE),  # Bounded queue for progress updates
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
        _emit_progress(job_id, "Starting diarization", "diarization")

        filename = file.filename or "audio.mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            # Note: Actual diarization logic would go here
            # For now, placeholder result
            _emit_progress(job_id, "Processing audio for speaker segments", "diarization")
            result = f"Diarization result for {filename}"

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result
            _emit_progress(job_id, "Diarization complete", "diarization")

        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        _emit_progress(job_id, f"Diarization failed: {e}", "error")


async def _process_transcription(
    job_id: str,
    content: bytes,
    filename: str,
    api_key: str,
    _diarize: bool = False,  # noqa: FBT001, FBT002
    _hf_token: str | None = None,
    _device: str | None = None,
    translate_to: str | None = None,
) -> None:
    """Process transcription job asynchronously."""
    start_time = time.time()

    logger.info(
        "Starting transcription job processing",
        extra={
            "job_id": job_id,
            "file_name": filename,
            "translate_to": translate_to,
        },
    )

    # Note: diarize, hf_token, device will be used when integrating diarization
    try:
        jobs[job_id]["status"] = "processing"
        _emit_progress(job_id, "Starting transcription", "info")

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            transcriber = VideoTranscriber(api_key)

            # Detect language before transcription
            _emit_progress(job_id, "Detecting language", "language")
            detected_language = await asyncio.to_thread(transcriber.detect_language, tmp_path)
            jobs[job_id]["detected_language"] = detected_language
            _emit_progress(job_id, f"Detected language: {detected_language}", "language")

            # Transcribe audio
            _emit_progress(job_id, "Transcribing audio", "info")
            result = await asyncio.to_thread(transcriber.transcribe, tmp_path)
            _emit_progress(job_id, "Transcription complete", "info")

            # If translation requested, translate the transcript
            if translate_to:
                _emit_progress(job_id, f"Translating to {translate_to}", "translation")
                translator = AudioTranslator(api_key)
                result = await asyncio.to_thread(
                    translator.translate_transcript, result, translate_to, preserve_timestamps=True
                )
                jobs[job_id]["translated_to"] = translate_to
                _emit_progress(job_id, f"Translation to {translate_to} complete", "translation")

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result
            _emit_progress(job_id, "Job completed successfully", "info")

            duration = time.time() - start_time
            logger.info(
                "Transcription job completed successfully",
                extra={
                    "job_id": job_id,
                    "duration_seconds": round(duration, 2),
                    "result_length": len(result),
                },
            )

        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    except Exception as e:
        duration = time.time() - start_time
        logger.exception(
            "Transcription job failed",
            extra={
                "job_id": job_id,
                "duration_seconds": round(duration, 2),
                "error": str(e),
            },
        )
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        _emit_progress(job_id, f"Transcription failed: {e}", "error")


def _parse_transcript_segments(transcript: str) -> list[dict[str, Any]]:
    """Parse transcript text into segments with timestamps.

    Args:
        transcript: Formatted transcript text with timestamps

    Returns:
        List of segment dictionaries with start, end, text, and optional speaker
    """
    segments = []
    lines = transcript.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try to match format with speaker: [Speaker] [HH:MM:SS - HH:MM:SS] text
        speaker_match = re.match(r"^\[([^\]]+)\]\s*\[(\d{2}):(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2}):(\d{2})\]\s*(.+)$", line)
        if speaker_match:
            speaker, start_h, start_m, start_s, end_h, end_m, end_s, text = speaker_match.groups()
            segments.append(
                {
                    "speaker": speaker,
                    "start": int(start_h) * 3600 + int(start_m) * 60 + int(start_s),
                    "end": int(end_h) * 3600 + int(end_m) * 60 + int(end_s),
                    "text": text.strip(),
                }
            )
            continue

        # Try to match format without speaker: [HH:MM:SS - HH:MM:SS] text
        no_speaker_match = re.match(r"^\[(\d{2}):(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2}):(\d{2})\]\s*(.+)$", line)
        if no_speaker_match:
            start_h, start_m, start_s, end_h, end_m, end_s, text = no_speaker_match.groups()
            segments.append(
                {
                    "start": int(start_h) * 3600 + int(start_m) * 60 + int(start_s),
                    "end": int(end_h) * 3600 + int(end_m) * 60 + int(end_s),
                    "text": text.strip(),
                }
            )

    return segments


def _format_as_txt(segments: list[dict[str, Any]]) -> str:
    """Format segments as plain text."""
    lines = []
    for seg in segments:
        speaker_prefix = f"[{seg['speaker']}] " if seg.get("speaker") else ""
        lines.append(f"{speaker_prefix}{seg['text']}")
    return "\n".join(lines)


def _format_as_vtt(segments: list[dict[str, Any]]) -> str:
    """Format segments as WebVTT."""
    lines = ["WEBVTT", ""]

    for i, seg in enumerate(segments, 1):
        start_time = _format_vtt_time(seg["start"])
        end_time = _format_vtt_time(seg["end"])
        lines.append(str(i))
        lines.append(f"{start_time} --> {end_time}")
        if seg.get("speaker"):
            lines.append(f"<v {seg['speaker']}>{seg['text']}")
        else:
            lines.append(seg["text"])
        lines.append("")

    return "\n".join(lines)


def _format_as_srt(segments: list[dict[str, Any]]) -> str:
    """Format segments as SRT."""
    lines = []

    for i, seg in enumerate(segments, 1):
        start_time = _format_srt_time(seg["start"])
        end_time = _format_srt_time(seg["end"])
        lines.append(str(i))
        lines.append(f"{start_time} --> {end_time}")
        speaker_prefix = f"[{seg['speaker']}] " if seg.get("speaker") else ""
        lines.append(f"{speaker_prefix}{seg['text']}")
        lines.append("")

    return "\n".join(lines)


def _format_vtt_time(seconds: int) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.000"


def _format_srt_time(seconds: int) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"


@router.get("/jobs/{job_id}/download")
async def download_transcript(
    job_id: str,
    format: str = Query("txt", pattern="^(txt|vtt|srt)$"),  # noqa: A002
) -> PlainTextResponse:
    """Download transcript in specified format.

    Args:
        job_id: Job ID
        format: Output format (txt, vtt, or srt)

    Returns:
        Formatted transcript file
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed. Status: {job['status']}")

    result = job.get("result", "")
    if not result:
        raise HTTPException(status_code=404, detail="No transcript available")

    # Parse transcript into segments
    segments = _parse_transcript_segments(result)

    if not segments:
        raise HTTPException(status_code=404, detail="No segments found in transcript")

    # Format based on requested type
    if format == "txt":
        content = _format_as_txt(segments)
        media_type = "text/plain"
    elif format == "vtt":
        content = _format_as_vtt(segments)
        media_type = "text/vtt"
    else:  # srt
        content = _format_as_srt(segments)
        media_type = "application/x-subrip"

    filename = f"transcript.{format}"
    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
