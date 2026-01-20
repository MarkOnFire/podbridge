"""Ingest router for Editorial Assistant v3.0 API.

Provides endpoints for remote ingest server monitoring and screengrab attachment.

Endpoints:
- GET /scan - Trigger scan of remote server
- GET /status - Get scanner status and file counts
- GET /screengrabs - List pending screengrabs
- POST /screengrabs/{file_id}/attach - Attach single screengrab to SST
- POST /screengrabs/attach-all - Attach all pending screengrabs
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.services.ingest_scanner import IngestScanner, ScanResult, get_ingest_scanner
from api.services.screengrab_attacher import (
    ScreengrabAttacher,
    AttachResult,
    BatchAttachResult,
    get_screengrab_attacher,
)
from api.services.database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter()


# Response models
class ScanResponse(BaseModel):
    """Response from scan endpoint."""
    success: bool
    new_files_found: int
    total_files_on_server: int
    scan_duration_ms: int
    new_transcripts: int
    new_screengrabs: int
    error_message: Optional[str] = None


class ScreengrabFile(BaseModel):
    """A screengrab file discovered on remote server."""
    id: int
    filename: str
    remote_url: str
    media_id: Optional[str]
    status: str
    first_seen_at: datetime
    sst_record_id: Optional[str] = None
    attached_at: Optional[datetime] = None


class ScreengrabListResponse(BaseModel):
    """Response listing screengrabs."""
    screengrabs: List[ScreengrabFile]
    total_new: int
    total_attached: int
    total_no_match: int


class AttachResponse(BaseModel):
    """Response from single attach operation."""
    success: bool
    media_id: str
    filename: str
    sst_record_id: Optional[str] = None
    attachments_before: int = 0
    attachments_after: int = 0
    error_message: Optional[str] = None
    skipped_duplicate: bool = False


class BatchAttachResponse(BaseModel):
    """Response from batch attach operation."""
    total_processed: int
    attached: int
    skipped_no_match: int
    skipped_duplicate: int
    errors: List[str]


class IngestStatusResponse(BaseModel):
    """Scanner status and configuration."""
    enabled: bool
    server_url: str
    files_by_status: dict
    files_by_type: dict


# Endpoints

@router.post("/scan", response_model=ScanResponse)
async def trigger_scan(
    base_url: str = Query(
        default="https://mmingest.pbswi.wisc.edu/",
        description="Base URL of ingest server"
    ),
    directories: Optional[str] = Query(
        default=None,
        description="Comma-separated list of directories to scan"
    ),
) -> ScanResponse:
    """
    Trigger a scan of the remote ingest server.

    Discovers new SRT transcripts and JPG screengrabs, tracking them
    in the database for further action.

    Args:
        base_url: Base URL of the ingest server
        directories: Comma-separated directory paths (default: root)

    Returns:
        Scan results including counts of new files discovered
    """
    try:
        dirs = directories.split(",") if directories else ["/"]
        scanner = IngestScanner(base_url=base_url, directories=dirs)
        result = await scanner.scan()

        return ScanResponse(
            success=result.success,
            new_files_found=result.new_files_found,
            total_files_on_server=result.total_files_on_server,
            scan_duration_ms=result.scan_duration_ms,
            new_transcripts=result.new_transcripts,
            new_screengrabs=result.new_screengrabs,
            error_message=result.error_message,
        )
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=IngestStatusResponse)
async def get_ingest_status() -> IngestStatusResponse:
    """
    Get current ingest scanner status and file counts.

    Returns counts of files by status and type.
    """
    async with get_session() as session:
        # Count by status
        status_query = text("""
            SELECT status, COUNT(*) as count
            FROM available_files
            GROUP BY status
        """)
        result = await session.execute(status_query)
        status_counts = {row.status: row.count for row in result.fetchall()}

        # Count by type
        type_query = text("""
            SELECT file_type, COUNT(*) as count
            FROM available_files
            GROUP BY file_type
        """)
        result = await session.execute(type_query)
        type_counts = {row.file_type: row.count for row in result.fetchall()}

    return IngestStatusResponse(
        enabled=True,
        server_url="https://mmingest.pbswi.wisc.edu/",
        files_by_status=status_counts,
        files_by_type=type_counts,
    )


@router.get("/screengrabs", response_model=ScreengrabListResponse)
async def list_screengrabs(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: new, attached, no_match, ignored"
    ),
    limit: int = Query(default=50, le=200),
) -> ScreengrabListResponse:
    """
    List screengrab files discovered on the ingest server.

    Args:
        status: Optional filter by status
        limit: Maximum results to return

    Returns:
        List of screengrab files with their status
    """
    async with get_session() as session:
        # Build query
        query = """
            SELECT id, remote_url, filename, media_id, status,
                   first_seen_at, airtable_record_id, attached_at
            FROM available_files
            WHERE file_type = 'screengrab'
        """
        params = {"limit": limit}

        if status:
            query += " AND status = :status"
            params["status"] = status

        query += " ORDER BY first_seen_at DESC LIMIT :limit"

        result = await session.execute(text(query), params)
        rows = result.fetchall()

        screengrabs = [
            ScreengrabFile(
                id=row.id,
                filename=row.filename,
                remote_url=row.remote_url,
                media_id=row.media_id,
                status=row.status,
                first_seen_at=row.first_seen_at,
                sst_record_id=row.airtable_record_id,
                attached_at=row.attached_at,
            )
            for row in rows
        ]

        # Get totals
        totals_query = text("""
            SELECT status, COUNT(*) as count
            FROM available_files
            WHERE file_type = 'screengrab'
            GROUP BY status
        """)
        result = await session.execute(totals_query)
        totals = {row.status: row.count for row in result.fetchall()}

    return ScreengrabListResponse(
        screengrabs=screengrabs,
        total_new=totals.get("new", 0),
        total_attached=totals.get("attached", 0),
        total_no_match=totals.get("no_match", 0),
    )


@router.post("/screengrabs/{file_id}/attach", response_model=AttachResponse)
async def attach_screengrab(file_id: int) -> AttachResponse:
    """
    Attach a single screengrab to its matching SST record.

    SAFETY: This operation APPENDS to existing attachments, never replaces them.

    Args:
        file_id: ID from available_files table

    Returns:
        Attachment result including before/after counts
    """
    try:
        attacher = get_screengrab_attacher()
        result = await attacher.attach_from_available_file(file_id)

        return AttachResponse(
            success=result.success,
            media_id=result.media_id,
            filename=result.filename,
            sst_record_id=result.sst_record_id,
            attachments_before=result.attachments_before,
            attachments_after=result.attachments_after,
            error_message=result.error_message,
            skipped_duplicate=result.skipped_duplicate,
        )
    except Exception as e:
        logger.error(f"Attach failed for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screengrabs/attach-all", response_model=BatchAttachResponse)
async def attach_all_screengrabs() -> BatchAttachResponse:
    """
    Attach all pending screengrabs that have matching SST records.

    SAFETY: This operation APPENDS to existing attachments, never replaces them.
    Each screengrab is processed individually with full audit logging.

    Returns:
        Batch results including counts of attached, skipped, and errors
    """
    try:
        attacher = get_screengrab_attacher()
        result = await attacher.attach_all_pending()

        return BatchAttachResponse(
            total_processed=result.total_processed,
            attached=result.attached,
            skipped_no_match=result.skipped_no_match,
            skipped_duplicate=result.skipped_duplicate,
            errors=result.errors,
        )
    except Exception as e:
        logger.error(f"Batch attach failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screengrabs/{file_id}/ignore")
async def ignore_screengrab(file_id: int) -> dict:
    """
    Mark a screengrab as ignored (won't appear in pending list).

    Args:
        file_id: ID from available_files table

    Returns:
        Success message
    """
    async with get_session() as session:
        query = text("""
            UPDATE available_files
            SET status = 'ignored',
                status_changed_at = :now
            WHERE id = :file_id AND file_type = 'screengrab'
        """)
        result = await session.execute(query, {
            "file_id": file_id,
            "now": datetime.utcnow().isoformat(),
        })

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Screengrab not found")

    return {"success": True, "message": f"Screengrab {file_id} ignored"}


@router.post("/screengrabs/{file_id}/unignore")
async def unignore_screengrab(file_id: int) -> dict:
    """
    Restore an ignored screengrab to 'new' status.

    Args:
        file_id: ID from available_files table

    Returns:
        Success message
    """
    async with get_session() as session:
        query = text("""
            UPDATE available_files
            SET status = 'new',
                status_changed_at = :now
            WHERE id = :file_id AND file_type = 'screengrab' AND status = 'ignored'
        """)
        result = await session.execute(query, {
            "file_id": file_id,
            "now": datetime.utcnow().isoformat(),
        })

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Screengrab not found or not currently ignored"
            )

    return {"success": True, "message": f"Screengrab {file_id} restored to new"}
