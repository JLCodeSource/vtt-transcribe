"""WebSocket endpoints for real-time job updates."""

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vtt_transcribe.api.routes.transcription import jobs

router = APIRouter(tags=["websockets"])


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job status updates."""
    await websocket.accept()

    if job_id not in jobs:
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
                message: dict[str, Any] = {
                    "job_id": job_id,
                    "status": current_status,
                    "filename": current_job.get("filename"),
                }
                
                # Include detected language if available
                if "detected_language" in current_job:
                    message["detected_language"] = current_job["detected_language"]
                
                # Include translation info if available
                if "translated_to" in current_job:
                    message["translated_to"] = current_job["translated_to"]

                if current_status == "completed":
                    message["result"] = current_job.get("result")
                elif current_status == "failed":
                    message["error"] = current_job.get("error")

                await websocket.send_json(message)
                last_status = current_status

                # Close connection after final status
                if current_status in ["completed", "failed"]:
                    await websocket.close()
                    break

            # Poll interval
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close(code=1011)
