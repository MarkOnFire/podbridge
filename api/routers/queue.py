"""Queue management router for Editorial Assistant v3.0 API.

Provides CRUD operations for the job queue.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from api.models.job import Job, JobCreate, JobStatus
from api.services import database


router = APIRouter()


@router.get("/", response_model=List[Job])
async def list_queue(
    status: Optional[JobStatus] = Query(
        default=JobStatus.pending,
        description="Filter by job status (null = all statuses)"
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
) -> List[Job]:
    """List jobs in the queue with optional filtering and pagination.

    By default returns pending jobs ordered by priority (descending) then ID.
    Set status to null to return jobs with any status.

    Args:
        status: Filter by job status (default: pending)
        limit: Maximum number of jobs to return (1-100, default: 50)
        offset: Number of jobs to skip for pagination (default: 0)

    Returns:
        List of Job records matching filter criteria
    """
    jobs = await database.list_jobs(status=status, limit=limit, offset=offset)
    return jobs


@router.post("/", response_model=Job, status_code=201)
async def add_to_queue(job_create: JobCreate) -> Job:
    """Add a new job to the queue.

    Creates a job record with status=pending and default values.
    Returns the complete job record with generated ID.

    Args:
        job_create: Job creation schema with required fields

    Returns:
        Complete Job record including generated ID and timestamps
    """
    job = await database.create_job(job_create)
    return job


@router.delete("/{job_id}", status_code=204)
async def remove_from_queue(job_id: int) -> None:
    """Remove a job from the queue.

    Permanently deletes the job record from the database.
    Returns 404 if job not found.

    Args:
        job_id: ID of job to delete

    Raises:
        HTTPException: 404 if job not found
    """
    deleted = await database.delete_job(job_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return None


@router.get("/next", response_model=Job)
async def get_next_job() -> Job:
    """Get the next pending job to process.

    Returns the highest priority pending job. If multiple jobs have
    the same priority, returns the earliest queued job.

    Returns 404 if no pending jobs exist.

    Returns:
        Next Job to process

    Raises:
        HTTPException: 404 if no pending jobs in queue
    """
    job = await database.get_next_pending_job()

    if job is None:
        raise HTTPException(status_code=404, detail="No pending jobs in queue")

    return job


@router.get("/stats")
async def get_queue_stats() -> dict:
    """Get queue statistics.

    Returns counts of jobs by status and other queue metrics.

    Returns:
        Dictionary with queue statistics:
        - pending: Number of jobs waiting to be processed
        - in_progress: Number of jobs currently processing
        - completed: Number of successfully completed jobs
        - failed: Number of failed jobs
        - cancelled: Number of cancelled jobs
        - paused: Number of paused jobs
        - total: Total number of jobs in database
    """
    # Get counts for each status
    pending_jobs = await database.list_jobs(status=JobStatus.pending, limit=1000)
    in_progress_jobs = await database.list_jobs(status=JobStatus.in_progress, limit=1000)
    completed_jobs = await database.list_jobs(status=JobStatus.completed, limit=1000)
    failed_jobs = await database.list_jobs(status=JobStatus.failed, limit=1000)
    cancelled_jobs = await database.list_jobs(status=JobStatus.cancelled, limit=1000)
    paused_jobs = await database.list_jobs(status=JobStatus.paused, limit=1000)

    pending_count = len(pending_jobs)
    in_progress_count = len(in_progress_jobs)
    completed_count = len(completed_jobs)
    failed_count = len(failed_jobs)
    cancelled_count = len(cancelled_jobs)
    paused_count = len(paused_jobs)

    total = (
        pending_count + in_progress_count + completed_count +
        failed_count + cancelled_count + paused_count
    )

    return {
        "pending": pending_count,
        "in_progress": in_progress_count,
        "completed": completed_count,
        "failed": failed_count,
        "cancelled": cancelled_count,
        "paused": paused_count,
        "total": total,
    }
