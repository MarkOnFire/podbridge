"""Integration tests for ScreengrabAttacher service.

CRITICAL: Tests verify that existing Airtable attachments are NEVER removed.
The ScreengrabAttacher must APPEND new attachments, never replace existing ones.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.screengrab_attacher import (
    AttachResult,
    BatchAttachResult,
    ScreengrabAttacher,
)


class TestAttachmentPreservation:
    """CRITICAL: Tests that verify existing attachments are preserved."""

    @pytest.mark.asyncio
    async def test_attach_preserves_existing_attachments(self):
        """CRITICAL: New attachment must be APPENDED, not replace existing."""
        # Existing attachments in SST record
        existing_attachments = [
            {"id": "att123", "filename": "old_image.jpg", "url": "https://example.com/old_image.jpg"},
            {"id": "att456", "filename": "another.jpg", "url": "https://example.com/another.jpg"},
        ]

        # Mock SST record with existing attachments
        mock_sst_record = {
            "id": "recXXXXXXXXXXXXXX",
            "fields": {
                "Media ID": "2WLI1209HD",
                "Screen Grab": existing_attachments,
            },
        }

        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Mock Airtable client for lookups
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=mock_sst_record)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session for audit logging
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock HTTP client for the update call
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_http_client.patch = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_http_client

            # Capture the payload sent to Airtable
            captured_payload = None

            async def capture_patch(url, headers=None, json=None):
                nonlocal captured_payload
                captured_payload = json
                return mock_response

            mock_http_client.patch = capture_patch

            # Create attacher and perform attach
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_screengrab(
                media_id="2WLI1209HD",
                filename="new_image.jpg",
                image_url="https://example.com/new_image.jpg",
            )

            # Verify success
            assert result.success is True
            assert result.attachments_before == 2
            assert result.attachments_after == 3

            # CRITICAL: Verify the payload preserves existing attachments
            assert captured_payload is not None
            screen_grab_field = captured_payload["fields"]["Screen Grab"]
            assert len(screen_grab_field) == 3

            # First two should be existing attachments (by ID)
            assert screen_grab_field[0] == {"id": "att123"}
            assert screen_grab_field[1] == {"id": "att456"}

            # Third should be new attachment (by URL)
            assert screen_grab_field[2]["url"] == "https://example.com/new_image.jpg"
            assert screen_grab_field[2]["filename"] == "new_image.jpg"

    @pytest.mark.asyncio
    async def test_attach_works_with_null_screen_grab_field(self):
        """Test that attachment works when Screen Grab field is null."""
        # Mock SST record with null Screen Grab field
        mock_sst_record = {
            "id": "recXXXXXXXXXXXXXX",
            "fields": {
                "Media ID": "2WLI1209HD",
                "Screen Grab": None,  # Field is null
            },
        }

        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Mock Airtable client
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=mock_sst_record)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock HTTP client
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            captured_payload = None

            async def capture_patch(url, headers=None, json=None):
                nonlocal captured_payload
                captured_payload = json
                return mock_response

            mock_http_client.patch = capture_patch
            mock_httpx.return_value.__aenter__.return_value = mock_http_client

            # Create attacher and perform attach
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_screengrab(
                media_id="2WLI1209HD",
                filename="first_image.jpg",
                image_url="https://example.com/first_image.jpg",
            )

            # Verify success
            assert result.success is True
            assert result.attachments_before == 0
            assert result.attachments_after == 1

            # Verify payload contains only the new attachment
            assert captured_payload is not None
            screen_grab_field = captured_payload["fields"]["Screen Grab"]
            assert len(screen_grab_field) == 1
            assert screen_grab_field[0]["url"] == "https://example.com/first_image.jpg"

    @pytest.mark.asyncio
    async def test_attach_works_with_empty_array_screen_grab_field(self):
        """Test that attachment works when Screen Grab field is an empty array."""
        # Mock SST record with empty Screen Grab array
        mock_sst_record = {
            "id": "recXXXXXXXXXXXXXX",
            "fields": {
                "Media ID": "2WLI1209HD",
                "Screen Grab": [],  # Field is empty array
            },
        }

        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Mock Airtable client
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=mock_sst_record)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock HTTP client
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            captured_payload = None

            async def capture_patch(url, headers=None, json=None):
                nonlocal captured_payload
                captured_payload = json
                return mock_response

            mock_http_client.patch = capture_patch
            mock_httpx.return_value.__aenter__.return_value = mock_http_client

            # Create attacher and perform attach
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_screengrab(
                media_id="2WLI1209HD",
                filename="first_image.jpg",
                image_url="https://example.com/first_image.jpg",
            )

            # Verify success
            assert result.success is True
            assert result.attachments_before == 0
            assert result.attachments_after == 1

            # Verify payload contains only the new attachment
            assert captured_payload is not None
            screen_grab_field = captured_payload["fields"]["Screen Grab"]
            assert len(screen_grab_field) == 1
            assert screen_grab_field[0]["url"] == "https://example.com/first_image.jpg"


class TestDuplicateDetection:
    """Tests for duplicate filename detection."""

    @pytest.mark.asyncio
    async def test_skip_when_filename_already_exists(self):
        """Test that attachment is skipped when filename already exists."""
        # Existing attachments with duplicate filename
        existing_attachments = [
            {"id": "att123", "filename": "image.jpg", "url": "https://example.com/image.jpg"},
        ]

        mock_sst_record = {
            "id": "recXXXXXXXXXXXXXX",
            "fields": {
                "Media ID": "2WLI1209HD",
                "Screen Grab": existing_attachments,
            },
        }

        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
        ):

            # Mock Airtable client
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=mock_sst_record)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Create attacher and try to attach duplicate
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_screengrab(
                media_id="2WLI1209HD",
                filename="image.jpg",  # Same filename
                image_url="https://example.com/image.jpg",
            )

            # Verify duplicate was detected
            assert result.success is True
            assert result.skipped_duplicate is True
            assert result.attachments_before == 1
            assert result.attachments_after == 1  # Count unchanged

    @pytest.mark.asyncio
    async def test_returns_skipped_duplicate_in_result(self):
        """Test that skipped_duplicate flag is set correctly in result."""
        # Existing attachments
        existing_attachments = [
            {"id": "att123", "filename": "duplicate.jpg", "url": "https://example.com/dup.jpg"},
        ]

        mock_sst_record = {
            "id": "recXXXXXXXXXXXXXX",
            "fields": {
                "Media ID": "2WLI1209HD",
                "Screen Grab": existing_attachments,
            },
        }

        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
        ):

            # Mock Airtable client
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=mock_sst_record)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Create attacher
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_screengrab(
                media_id="2WLI1209HD",
                filename="duplicate.jpg",
                image_url="https://example.com/dup.jpg",
            )

            # Verify result structure
            assert isinstance(result, AttachResult)
            assert result.success is True
            assert result.skipped_duplicate is True
            assert result.media_id == "2WLI1209HD"
            assert result.filename == "duplicate.jpg"


class TestNoMatchHandling:
    """Tests for handling when Media ID not found in SST."""

    @pytest.mark.asyncio
    async def test_returns_error_when_media_id_not_found(self):
        """Test that error is returned when Media ID not found in SST."""
        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
        ):

            # Mock Airtable client to return None (not found)
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=None)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Create attacher and try to attach
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_screengrab(
                media_id="UNKNOWN123",
                filename="image.jpg",
                image_url="https://example.com/image.jpg",
            )

            # Verify error result
            assert result.success is False
            assert result.error_message is not None
            assert "No SST record found" in result.error_message
            assert result.media_id == "UNKNOWN123"


class TestAuditLogging:
    """Tests for audit log creation."""

    @pytest.mark.asyncio
    async def test_audit_log_created_on_success(self):
        """Test that audit log entry is created on successful attachment."""
        mock_sst_record = {
            "id": "recXXXXXXXXXXXXXX",
            "fields": {
                "Media ID": "2WLI1209HD",
                "Screen Grab": [],
            },
        }

        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Mock Airtable client
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=mock_sst_record)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            captured_audit_params = None

            async def capture_execute(query, params):
                nonlocal captured_audit_params
                if "screengrab_attachments" in str(query):
                    captured_audit_params = params

            mock_db.execute = AsyncMock(side_effect=capture_execute)
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock HTTP client
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_http_client.patch = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_http_client

            # Create attacher and perform attach
            attacher = ScreengrabAttacher(api_key="fake_key")
            await attacher.attach_screengrab(
                media_id="2WLI1209HD",
                filename="image.jpg",
                image_url="https://example.com/image.jpg",
                available_file_id=123,
            )

            # Verify audit log was created
            assert captured_audit_params is not None
            assert captured_audit_params["media_id"] == "2WLI1209HD"
            assert captured_audit_params["filename"] == "image.jpg"
            assert captured_audit_params["available_file_id"] == 123
            assert captured_audit_params["success"] is True

    @pytest.mark.asyncio
    async def test_audit_log_created_on_failure(self):
        """Test that audit log entry is created on failed attachment."""
        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
        ):

            # Mock Airtable client to return None (not found)
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(return_value=None)
            mock_airtable_class.return_value = mock_airtable

            # Mock database session
            mock_db = MagicMock()
            captured_audit_params = None

            async def capture_execute(query, params):
                nonlocal captured_audit_params
                if "screengrab_attachments" in str(query):
                    captured_audit_params = params

            mock_db.execute = AsyncMock(side_effect=capture_execute)
            mock_session.return_value.__aenter__.return_value = mock_db

            # Create attacher and try to attach
            attacher = ScreengrabAttacher(api_key="fake_key")
            await attacher.attach_screengrab(
                media_id="UNKNOWN123",
                filename="image.jpg",
                image_url="https://example.com/image.jpg",
            )

            # Verify audit log was created with error
            assert captured_audit_params is not None
            assert captured_audit_params["media_id"] == "UNKNOWN123"
            assert captured_audit_params["success"] is False
            assert captured_audit_params["error_message"] is not None


class TestBatchAttachment:
    """Tests for batch attachment operations."""

    @pytest.mark.asyncio
    async def test_attach_all_pending_processes_multiple_files(self):
        """Test that attach_all_pending processes all pending screengrabs."""
        with (
            patch("api.services.screengrab_attacher.AirtableClient") as mock_airtable_class,
            patch("api.services.screengrab_attacher.get_session") as mock_session,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            # Mock database session - return 2 pending screengrabs
            mock_db = MagicMock()
            mock_result = MagicMock()

            mock_row1 = MagicMock()
            mock_row1.id = 1
            mock_row1.remote_url = "https://example.com/image1.jpg"
            mock_row1.filename = "2WLI1209HD.jpg"
            mock_row1.media_id = "2WLI1209HD"

            mock_row2 = MagicMock()
            mock_row2.id = 2
            mock_row2.remote_url = "https://example.com/image2.jpg"
            mock_row2.filename = "2WLI1210HD.jpg"
            mock_row2.media_id = "2WLI1210HD"

            mock_result.fetchall.return_value = [mock_row1, mock_row2]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock Airtable client
            mock_airtable = MagicMock()
            mock_airtable.search_sst_by_media_id = AsyncMock(
                side_effect=[
                    {"id": "recXXX1", "fields": {"Media ID": "2WLI1209HD", "Screen Grab": []}},
                    {"id": "recXXX2", "fields": {"Media ID": "2WLI1210HD", "Screen Grab": []}},
                ]
            )
            mock_airtable_class.return_value = mock_airtable

            # Mock HTTP client
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_http_client.patch = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_http_client

            # Create attacher and run batch
            attacher = ScreengrabAttacher(api_key="fake_key")
            result = await attacher.attach_all_pending()

            # Verify batch results
            assert isinstance(result, BatchAttachResult)
            assert result.total_processed == 2
            assert result.attached == 2
            assert result.skipped_no_match == 0
            assert result.skipped_duplicate == 0
            assert len(result.errors) == 0
