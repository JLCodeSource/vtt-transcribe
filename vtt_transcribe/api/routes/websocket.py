"""WebSocket endpoints for real-time updates."""

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vtt_transcribe.api.routes.transcription import jobs

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job status updates.

    Args:
        websocket: WebSocket connection
        job_id: The job ID to monitor

    The WebSocket will send status updates as JSON messages with the format:
    {
        "job_id": "...",
        "status": "pending|processing|completed|failed",
        "filename": "...",
        ...
    }
    """
    await websocket.accept()

    try:
        # Check if job exists
        if job_id not in jobs:
            await websocket.send_json({"error": "Job not found", "status": "not_found"})
            await websocket.close()
            return

        # Send initial status
        await websocket.send_json(jobs[job_id])

        # Monitor job status and send updates
        last_status = jobs[job_id].get("status")

        while True:
            # Check for status changes
            current_job = jobs.get(job_id)
            if not current_job:
                break

            current_status = current_job.get("status")

            # Send update if status changed
            if current_status != last_status:
                await websocket.send_json(current_job)
                last_status = current_status

                # Close connection after terminal status
                if current_status in ("completed", "failed"):
                    break

            # Wait before checking again
            await asyncio.sleep(0.5)

        await websocket.close()

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        # Log error and close
        with contextlib.suppress(Exception):
            await websocket.send_json({"error": str(e)})
        await websocket.close()
