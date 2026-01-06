"""Jobs router for Editorial Assistant v3.0 API.

Provides endpoints for job detail retrieval, updates, and control operations.
"""

import os
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional

from api.models.job import Job, JobUpdate, JobStatus
from api.models.events import SessionEvent
from api.services.database import (
    get_job,
    update_job,
    get_events_for_job,
)
from api.services.airtable import AirtableClient

logger = logging.getLogger(__name__)


class SSTMetadata(BaseModel):
    """SST (Single Source of Truth) metadata from Airtable."""
    media_id: Optional[str] = None
    release_title: Optional[str] = None
    short_description: Optional[str] = None
    media_manager_url: Optional[str] = None
    youtube_url: Optional[str] = None
    airtable_url: Optional[str] = None


router = APIRouter()


# Valid state transitions for job control operations
PAUSEABLE_STATES = {JobStatus.pending, JobStatus.in_progress}
RESUMABLE_STATES = {JobStatus.paused}
RETRYABLE_STATES = {JobStatus.failed}
CANCELLABLE_STATES = {
    JobStatus.pending,
    JobStatus.in_progress,
    JobStatus.paused,
}


@router.get("/{job_id}", response_model=Job)
async def get_job_detail(job_id: int):
    """Retrieve full details for a specific job.

    Args:
        job_id: Job ID to retrieve

    Returns:
        Complete job record with all fields

    Raises:
        HTTPException: 404 if job not found
    """
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job


@router.patch("/{job_id}", response_model=Job)
async def update_job_fields(job_id: int, job_update: JobUpdate):
    """Update job fields with partial data.

    Accepts any subset of updateable fields and applies them to the job.

    Args:
        job_id: Job ID to update
        job_update: Partial update schema with optional fields

    Returns:
        Updated job record

    Raises:
        HTTPException: 404 if job not found
    """
    updated_job = await update_job(job_id, job_update)

    if updated_job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return updated_job


@router.post("/{job_id}/pause", response_model=Job)
async def pause_job(job_id: int):
    """Pause a running or pending job.

    Sets job status to 'paused'. Only valid for pending or in_progress jobs.

    Args:
        job_id: Job ID to pause

    Returns:
        Updated job record

    Raises:
        HTTPException: 404 if job not found, 400 if invalid state transition
    """
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in PAUSEABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause job in status '{job.status}'. "
                   f"Only {', '.join(s.value for s in PAUSEABLE_STATES)} jobs can be paused."
        )

    job_update = JobUpdate(status=JobStatus.paused)
    updated_job = await update_job(job_id, job_update)

    return updated_job


@router.post("/{job_id}/resume", response_model=Job)
async def resume_job(job_id: int):
    """Resume a paused job.

    Sets job status back to 'pending' so it can be picked up by the worker.
    Only valid for paused jobs.

    Args:
        job_id: Job ID to resume

    Returns:
        Updated job record

    Raises:
        HTTPException: 404 if job not found, 400 if invalid state transition
    """
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in RESUMABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume job in status '{job.status}'. "
                   f"Only {', '.join(s.value for s in RESUMABLE_STATES)} jobs can be resumed."
        )

    job_update = JobUpdate(status=JobStatus.pending)
    updated_job = await update_job(job_id, job_update)

    return updated_job


@router.post("/{job_id}/retry", response_model=Job)
async def retry_job(job_id: int):
    """Retry a failed job.

    Resets job status to 'pending' and clears error message.
    Only valid for failed jobs.

    Args:
        job_id: Job ID to retry

    Returns:
        Updated job record

    Raises:
        HTTPException: 404 if job not found, 400 if invalid state transition
    """
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in RETRYABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job in status '{job.status}'. "
                   f"Only {', '.join(s.value for s in RETRYABLE_STATES)} jobs can be retried."
        )

    # Reset to pending and clear error
    job_update = JobUpdate(
        status=JobStatus.pending,
        error_message="",  # Clear error message
        current_phase=None,  # Reset phase
    )
    updated_job = await update_job(job_id, job_update)

    return updated_job


@router.post("/{job_id}/cancel", response_model=Job)
async def cancel_job(job_id: int):
    """Cancel a job.

    Sets job status to 'cancelled'. Only valid for pending, in_progress, or paused jobs.
    Cannot cancel completed or failed jobs.

    Args:
        job_id: Job ID to cancel

    Returns:
        Updated job record

    Raises:
        HTTPException: 404 if job not found, 400 if invalid state transition
    """
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in CANCELLABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in status '{job.status}'. "
                   f"Only {', '.join(s.value for s in CANCELLABLE_STATES)} jobs can be cancelled."
        )

    job_update = JobUpdate(status=JobStatus.cancelled)
    updated_job = await update_job(job_id, job_update)

    return updated_job


@router.get("/{job_id}/events", response_model=List[SessionEvent])
async def get_job_events(job_id: int):
    """Retrieve all events for a specific job.

    Returns chronologically ordered list of events logged during job execution.
    Useful for debugging, monitoring, and audit trails.

    Args:
        job_id: Job ID to get events for

    Returns:
        List of SessionEvent records ordered by timestamp

    Raises:
        HTTPException: 404 if job not found
    """
    # Verify job exists
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    events = await get_events_for_job(job_id)

    return events


@router.get("/{job_id}/outputs/{filename}")
async def get_job_output(job_id: int, filename: str):
    """Retrieve an output file for a specific job.

    Returns the contents of a generated output file (markdown, json, etc.).
    File must exist in the job's output directory.

    Args:
        job_id: Job ID to get output for
        filename: Name of the output file (e.g., analyst_output.md)

    Returns:
        File contents as plain text

    Raises:
        HTTPException: 404 if job or file not found, 400 if invalid filename
    """
    # Verify job exists
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Security: only allow specific safe filenames
    allowed_files = {
        "analyst_output.md",
        "formatter_output.md",
        "seo_output.md",
        "manager_output.md",
        "copy_editor_output.md",
        "recovery_analysis.md",
        "manifest.json",
    }

    if filename not in allowed_files:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename. Allowed files: {', '.join(sorted(allowed_files))}"
        )

    # Build path to output file
    if not job.project_path:
        raise HTTPException(
            status_code=404,
            detail="Job has no output directory configured"
        )

    # Security: Resolve paths and validate within OUTPUT directory
    output_dir = Path(os.getenv("OUTPUT_DIR", "OUTPUT")).resolve()
    file_path = (Path(job.project_path) / filename).resolve()

    # Prevent path traversal attacks
    if not file_path.is_relative_to(output_dir):
        raise HTTPException(
            status_code=400,
            detail="Invalid project path - outside output directory"
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Output file '{filename}' not found for job {job_id}"
        )

    # Read and return file contents
    content = file_path.read_text(encoding="utf-8")

    # Determine content type
    if filename.endswith(".json"):
        return PlainTextResponse(content, media_type="application/json")
    else:
        return PlainTextResponse(content, media_type="text/markdown")


@router.get("/{job_id}/sst-metadata", response_model=SSTMetadata)
async def get_sst_metadata(job_id: int):
    """Retrieve SST (Single Source of Truth) metadata from Airtable for a job.

    Returns contextual metadata from PBS Wisconsin's Airtable SST table,
    including release title, descriptions, and external links.

    This is a READ-ONLY operation against Airtable.

    Args:
        job_id: Job ID to get SST metadata for

    Returns:
        SSTMetadata with available fields from Airtable

    Raises:
        HTTPException: 404 if job not found or no Airtable record linked
    """
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not job.airtable_record_id:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} has no linked Airtable record"
        )

    try:
        client = AirtableClient()
        record = await client.get_sst_record(job.airtable_record_id)

        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"Airtable record {job.airtable_record_id} not found"
            )

        fields = record.get("fields", {})

        return SSTMetadata(
            media_id=fields.get("Media ID"),
            release_title=fields.get("Release Title"),
            short_description=fields.get("Short Description"),
            media_manager_url=fields.get("Final Website Link"),  # PBS Wisconsin website URL
            youtube_url=fields.get("YouTube Link"),
            airtable_url=client.get_sst_url(job.airtable_record_id),
        )

    except ValueError as e:
        # Airtable API key not configured
        logger.warning(f"Airtable not configured: {e}")
        raise HTTPException(
            status_code=503,
            detail="Airtable integration not configured"
        )
    except Exception as e:
        logger.error(f"Failed to fetch SST metadata: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch metadata from Airtable"
        )
