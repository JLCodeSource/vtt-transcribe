"""Transcription API endpoints."""

import asyncio
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse

from vtt_transcribe.transcriber import VideoTranscriber
from vtt_transcribe.translator import AudioTranslator

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
        "translate_to": translate_to,
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

    return jobs[job_id]


@router.post("/detect-language")
async def detect_language(
    file: UploadFile = File(...),  # noqa: B008
    api_key: str = Form(...),
) -> dict[str, str]:
    """Detect language of audio file.

    Args:
        file: Audio or video file
        api_key: OpenAI API key

    Returns:
        Detected language code and name
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
    translate_to: str | None = None,
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

            # If translation requested, translate the transcript
            if translate_to:
                translator = AudioTranslator(api_key)
                result = await asyncio.to_thread(
                    translator.translate_transcript, result, translate_to, preserve_timestamps=True
                )
                jobs[job_id]["translated_to"] = translate_to

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result

        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


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
    format: str = Query("txt", regex="^(txt|vtt|srt)$"),  # noqa: A002
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
