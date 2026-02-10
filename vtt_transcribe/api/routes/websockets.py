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


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job status updates."""
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

            # Send update if status changed
            if current_status != last_status:
                message = _build_status_message(job_id, current_job)
                await websocket.send_json(message)
                last_status = current_status

                # Close connection after final status
                if current_status in ["completed", "failed"]:
                    await websocket.close()
                    break

            # Poll interval
            await asyncio.sleep(0.5)

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
