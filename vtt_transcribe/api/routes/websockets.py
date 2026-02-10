"""WebSocket endpoints for real-time job updates."""

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vtt_transcribe.api.routes.transcription import jobs
from vtt_transcribe.logging_config import get_logger

router = APIRouter(tags=["websockets"])
logger = get_logger(__name__)


def _build_status_message(job_id: str, current_job: dict[str, Any]) -> dict[str, Any]:
    """Build status update message from job data."""
    current_status = current_job.get("status")
    message: dict[str, Any] = {
        "job_id": job_id,
        "status": current_status,
        "filename": current_job.get("filename"),
    }

    # Include optional fields if available
    if "detected_language" in current_job:
        message["detected_language"] = current_job["detected_language"]
    if "translated_to" in current_job:
        message["translated_to"] = current_job["translated_to"]

    # Include result/error based on status
    if current_status == "completed":
        message["result"] = current_job.get("result")
    elif current_status == "failed":
        message["error"] = current_job.get("error")

    return message


async def _wait_for_progress_or_timeout(progress_queue: asyncio.Queue, timeout: float = 0.5) -> dict[str, Any] | None:
    """Wait for a progress update from queue with timeout.
    
    Args:
        progress_queue: Queue to wait on
        timeout: Timeout in seconds
        
    Returns:
        Progress update dict or None if timeout
    """
    try:
        return await asyncio.wait_for(progress_queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


async def _drain_progress_queue(websocket: WebSocket, job_id: str, progress_queue: asyncio.Queue) -> None:
    """Drain all pending progress updates from the queue and send to WebSocket.
    
    Args:
        websocket: WebSocket connection
        job_id: Job identifier to add to progress messages
        progress_queue: Queue containing progress updates
    """
    while not progress_queue.empty():
        try:
            progress_update = progress_queue.get_nowait()
            # Add job_id to progress message
            progress_update["job_id"] = job_id
            await websocket.send_json(progress_update)
        except asyncio.QueueEmpty:
            break


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job status and progress updates.

    Streams both:
    - Status changes (pending -> processing -> completed/failed)
    - Detailed progress events (language detection, transcription progress, diarization, translation)
    """
    logger.info(
        "WebSocket connection initiated",
        extra={"job_id": job_id},
    )

    await websocket.accept()
    logger.info(
        "WebSocket connection accepted",
        extra={"job_id": job_id},
    )

    if job_id not in jobs:
        logger.warning(
            "WebSocket connection for unknown job",
            extra={"job_id": job_id},
        )
        await websocket.send_json({"error": "Job not found", "job_id": job_id})
        await websocket.close(code=1008)
        return

    try:
        last_status = None

        while True:
            if job_id not in jobs:
                await websocket.send_json({"error": "Job deleted"})
                break

            current_job = jobs[job_id]
            current_status = current_job.get("status")

            # Send status update if changed
            if current_status != last_status:
                message = _build_status_message(job_id, current_job)
                await websocket.send_json(message)
                last_status = current_status

                # Drain any final progress events before closing
                if current_status in ["completed", "failed"]:
                    # Give a moment for final progress events to be queued
                    await asyncio.sleep(0.1)
                    # Drain any remaining progress events
                    if "progress_updates" in current_job:
                        await _drain_progress_queue(websocket, job_id, current_job["progress_updates"])
                    await websocket.close()
                    break

            # Stream any queued progress updates (drain immediately available)
            if "progress_updates" in current_job:
                await _drain_progress_queue(websocket, job_id, current_job["progress_updates"])

            # Wait for next progress update or timeout (more efficient than tight polling)
            if "progress_updates" in current_job:
                progress_update = await _wait_for_progress_or_timeout(current_job["progress_updates"], timeout=0.5)
                if progress_update:
                    progress_update["job_id"] = job_id
                    await websocket.send_json(progress_update)

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected by client",
            extra={"job_id": job_id},
        )
    except Exception as e:
        logger.exception(
            "WebSocket error",
            extra={"job_id": job_id, "error": str(e)},
        )
        await websocket.send_json({"error": str(e)})
        await websocket.close(code=1011)
