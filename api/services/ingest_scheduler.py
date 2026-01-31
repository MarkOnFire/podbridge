"""Ingest scanner scheduler for Sprint 11.1.

Manages scheduled scanning of the ingest server using APScheduler.
Configures scan timing based on database config values.
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from api.services.ingest_config import (
    get_ingest_config,
    parse_scan_time,
    record_scan_result,
)
from api.services.ingest_scanner import get_ingest_scanner

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def run_scheduled_scan():
    """Execute a scheduled scan of the ingest server.

    This is the job function called by APScheduler on the configured schedule.
    """
    logger.info("Starting scheduled ingest scan")

    try:
        # Get current config
        config = await get_ingest_config()

        # Create scanner with config values
        scanner = get_ingest_scanner(
            base_url=config.server_url,
            directories=config.directories,
        )

        # Run scan
        result = await scanner.scan()

        # Record result
        await record_scan_result(success=result.success)

        if result.success:
            logger.info(
                f"Scheduled scan complete: checked {result.qc_passed_checked} Media IDs, "
                f"found {result.new_files_found} new files "
                f"({result.new_transcripts} transcripts, {result.new_screengrabs} screengrabs)"
            )
        else:
            logger.error(f"Scheduled scan failed: {result.error_message}")

    except Exception as e:
        logger.error(f"Scheduled scan error: {e}", exc_info=True)
        await record_scan_result(success=False)


async def configure_scheduler():
    """Configure or reconfigure the scheduler based on current database config.

    Called at startup and whenever config is updated via the API.
    """
    config = await get_ingest_config()
    scheduler = get_scheduler()

    # Remove existing job if present
    if scheduler.get_job("ingest_scan"):
        scheduler.remove_job("ingest_scan")
        logger.info("Removed existing ingest scan job")

    # Only add job if scanning is enabled
    if not config.enabled:
        logger.info("Ingest scanning is disabled, no job scheduled")
        return

    # Parse scan time (HH:MM format)
    try:
        hour, minute = parse_scan_time(config.scan_time)
    except ValueError as e:
        logger.error(f"Invalid scan_time in config: {config.scan_time} - {e}")
        return

    # Create cron trigger for daily execution at configured time
    trigger = CronTrigger(hour=hour, minute=minute)

    # Add job to scheduler
    scheduler.add_job(
        run_scheduled_scan,
        trigger=trigger,
        id="ingest_scan",
        name="Ingest Server Scan",
        replace_existing=True,
    )

    # Log the scheduled time
    job = scheduler.get_job("ingest_scan")
    if job:
        # Get next run time - may be None if scheduler not started yet
        try:
            next_run = getattr(job, "next_run_time", None)
            if next_run:
                logger.info(f"Ingest scan scheduled: daily at {config.scan_time} (next run: {next_run})")
            else:
                logger.info(f"Ingest scan scheduled: daily at {config.scan_time}")
        except Exception:
            logger.info(f"Ingest scan scheduled: daily at {config.scan_time}")


async def start_scheduler():
    """Initialize and start the scheduler.

    Called during application startup.
    """
    scheduler = get_scheduler()

    # Configure based on current config
    await configure_scheduler()

    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()
        logger.info("Ingest scheduler started")


async def stop_scheduler():
    """Stop the scheduler.

    Called during application shutdown.
    """
    scheduler = get_scheduler()

    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Ingest scheduler stopped")
