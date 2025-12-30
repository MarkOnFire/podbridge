#!/usr/bin/env python3
"""CLI entry point for the job processing worker.

Usage:
    ./venv/bin/python run_worker.py

Or with custom options:
    ./venv/bin/python run_worker.py --poll-interval 60 --heartbeat-interval 30
"""
import argparse
import asyncio
import signal
import sys

from api.services.worker import JobWorker, WorkerConfig
from api.services.database import init_db, close_db
from api.services.llm import get_llm_client, close_llm_client


async def main(args):
    """Run the job processing worker."""
    # Initialize database
    await init_db()

    # Initialize LLM client
    get_llm_client()

    # Create worker config
    config = WorkerConfig(
        poll_interval=args.poll_interval,
        heartbeat_interval=args.heartbeat_interval,
        max_retries=args.max_retries,
    )

    # Create and start worker
    worker = JobWorker(config)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        print("\n[Worker] Shutdown signal received, stopping...")
        asyncio.create_task(worker.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    try:
        print("[Worker] Starting Editorial Assistant job worker...")
        print(f"[Worker] Poll interval: {args.poll_interval}s")
        print(f"[Worker] Heartbeat interval: {args.heartbeat_interval}s")
        print(f"[Worker] Max retries: {args.max_retries}")
        print("[Worker] Press Ctrl+C to stop")
        print()

        await worker.start()
    finally:
        # Cleanup
        await close_llm_client()
        await close_db()
        print("[Worker] Shutdown complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Editorial Assistant job processing worker"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between queue polling (default: 30)",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=60,
        help="Seconds between heartbeat updates (default: 60)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts for failed jobs (default: 3)",
    )

    args = parser.parse_args()
    asyncio.run(main(args))
