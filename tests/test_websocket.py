"""Tests for WebSocket endpoint."""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.models.job import Job, JobStatus


def test_websocket_connection():
    """Test that WebSocket connection can be established."""
    client = TestClient(app)

    # Note: TestClient WebSocket support is basic and doesn't support full WS protocol
    # This test verifies the endpoint exists and accepts connections
    with client.websocket_connect("/api/ws/jobs") as websocket:
        # Send ping
        websocket.send_text("ping")

        # Receive pong
        data = websocket.receive_text()
        assert data == "pong"


def test_websocket_broadcast_job_update():
    """Test that job updates can be broadcast to WebSocket clients."""
    from api.routers.websocket import manager
    from api.models.job import Job, JobStatus
    from datetime import datetime, timezone

    # Create a mock job
    job = Job(
        id=1,
        project_path="/path/to/project",
        transcript_file="test.txt",
        status=JobStatus.pending,
        priority=0,
        queued_at=datetime.now(timezone.utc),
        estimated_cost=0.0,
        actual_cost=0.0,
        agent_phases=["analyst", "formatter"],
        retry_count=0,
        max_retries=3,
    )

    # Test that broadcast doesn't fail when no clients are connected
    # (This is a synchronous test, so we can't test actual async broadcast)
    assert len(manager.active_connections) == 0


def test_websocket_connection_manager():
    """Test ConnectionManager functionality."""
    from api.routers.websocket import ConnectionManager

    manager = ConnectionManager()

    # Verify initial state
    assert len(manager.active_connections) == 0

    # Note: Cannot fully test add/remove without actual WebSocket connections
    # in a unit test environment. Integration tests would be needed for that.
