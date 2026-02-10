"""Job history and transcript storage routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vtt_transcribe.api.auth import get_current_active_user
from vtt_transcribe.api.database import get_db
from vtt_transcribe.api.models import TranscriptionJob, User

router = APIRouter(prefix="/jobs", tags=["job-history"])


# Response models
class JobSummary(BaseModel):
    """Job summary for list view."""

    model_config = {"from_attributes": True}

    id: int
    job_id: str
    filename: str
    status: str
    detected_language: str | None
    translated_to: str | None
    with_diarization: bool
    created_at: datetime
    completed_at: datetime | None


class JobDetail(BaseModel):
    """Detailed job information including transcript."""

    model_config = {"from_attributes": True}

    id: int
    job_id: str
    filename: str
    status: str
    transcript: str | None
    error: str | None
    detected_language: str | None
    translated_to: str | None
    with_diarization: bool
    created_at: datetime
    completed_at: datetime | None


@router.get("/", response_model=list[JobSummary])
async def list_user_jobs(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, description="Filter by status: pending, processing, completed, failed"),
    limit: int = Query(50, ge=1, le=100, description="Number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
) -> list[TranscriptionJob]:
    """List all transcription jobs for the current user."""
    query = select(TranscriptionJob).where(TranscriptionJob.user_id == current_user.id)

    if status_filter:
        query = query.where(TranscriptionJob.status == status_filter)

    query = query.order_by(TranscriptionJob.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=JobDetail)
async def get_job_detail(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TranscriptionJob:
    """Get detailed information about a specific job."""
    result = await db.execute(
        select(TranscriptionJob).where(TranscriptionJob.job_id == job_id, TranscriptionJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a job from history."""
    result = await db.execute(
        select(TranscriptionJob).where(TranscriptionJob.job_id == job_id, TranscriptionJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await db.delete(job)
    await db.commit()


@router.get("/stats/summary")
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get statistics about user's transcription jobs."""
    from sqlalchemy import func

    # Get total count and status breakdown
    result = await db.execute(
        select(
            func.count(TranscriptionJob.id).label("total"),
            func.sum(TranscriptionJob.status == "completed").label("completed"),
            func.sum(TranscriptionJob.status == "failed").label("failed"),
            func.sum(TranscriptionJob.status == "processing").label("processing"),
            func.sum(TranscriptionJob.status == "pending").label("pending"),
        ).where(TranscriptionJob.user_id == current_user.id)
    )

    stats = result.one()

    return {
        "total_jobs": stats.total or 0,
        "completed": stats.completed or 0,
        "failed": stats.failed or 0,
        "processing": stats.processing or 0,
        "pending": stats.pending or 0,
    }
