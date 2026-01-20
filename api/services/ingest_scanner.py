"""
Ingest Scanner Service

Monitors remote ingest server (mmingest.pbswi.wisc.edu) for new files.
Parses Apache/nginx directory listings to discover SRT transcripts and JPG screengrabs.

File type routing:
- .srt/.txt files -> tracked for manual queue action (transcripts)
- .jpg/.jpeg/.png files -> auto-attached to SST records (screengrabs)
"""

import re
import logging
from datetime import datetime, timezone
from typing import Optional, List
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text

from api.services.database import get_session

logger = logging.getLogger(__name__)


@dataclass
class RemoteFile:
    """Represents a file discovered on the remote server."""
    filename: str
    url: str
    directory_path: str
    file_type: str  # 'transcript' or 'screengrab'
    media_id: Optional[str] = None
    file_size_bytes: Optional[int] = None
    modified_at: Optional[datetime] = None


@dataclass
class ScanResult:
    """Result of scanning the remote server."""
    success: bool
    new_files_found: int
    total_files_on_server: int
    scan_duration_ms: int
    error_message: Optional[str] = None
    new_transcripts: int = 0
    new_screengrabs: int = 0


class IngestScanner:
    """
    Monitors remote ingest server for new SRT and JPG files.

    Parses Apache/nginx autoindex directory listings to discover files,
    extracts Media IDs from filenames, and tracks discoveries in the database.
    """

    # Media ID patterns (PBS Wisconsin conventions)
    # Pattern: 4 characters + 4 digits + optional 2 characters (e.g., 2WLI1209HD, 9UNP2005)
    MEDIA_ID_PATTERN = re.compile(r'([A-Z0-9]{4}\d{4}[A-Z]{0,2})', re.IGNORECASE)

    # File extensions by type
    TRANSCRIPT_EXTENSIONS = {'.srt', '.txt'}
    SCREENGRAB_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

    def __init__(
        self,
        base_url: str = "https://mmingest.pbswi.wisc.edu/",
        directories: Optional[List[str]] = None,
        timeout_seconds: int = 30,
        auth: Optional[tuple] = None,
    ):
        """
        Initialize scanner.

        Args:
            base_url: Base URL of the ingest server
            directories: List of directory paths to scan (e.g., ["/exports/", "/images/"])
            timeout_seconds: HTTP request timeout
            auth: Optional (username, password) tuple for basic auth
        """
        self.base_url = base_url.rstrip('/')
        self.directories = directories or ["/"]
        self.timeout = timeout_seconds
        self.auth = auth

    async def scan(self) -> ScanResult:
        """
        Scan all configured directories for new files.

        Returns:
            ScanResult with scan statistics
        """
        import time
        start_time = time.time()

        result = ScanResult(
            success=False,
            new_files_found=0,
            total_files_on_server=0,
            scan_duration_ms=0,
        )

        try:
            all_files: List[RemoteFile] = []

            # Scan each configured directory
            for directory in self.directories:
                try:
                    dir_url = f"{self.base_url}{directory}"
                    files = await self._scan_directory(dir_url, directory)
                    all_files.extend(files)
                except Exception as e:
                    logger.warning(f"Failed to scan directory {directory}: {e}")

            result.total_files_on_server = len(all_files)

            # Process discovered files
            for remote_file in all_files:
                is_new = await self._track_file(remote_file)
                if is_new:
                    result.new_files_found += 1
                    if remote_file.file_type == 'transcript':
                        result.new_transcripts += 1
                    else:
                        result.new_screengrabs += 1

            result.success = True

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Scan failed: {e}")

        result.scan_duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def _scan_directory(
        self,
        url: str,
        directory_path: str,
    ) -> List[RemoteFile]:
        """
        Fetch and parse a directory listing.

        Args:
            url: Full URL to the directory
            directory_path: Path relative to base URL

        Returns:
            List of RemoteFile objects
        """
        files: List[RemoteFile] = []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            # Set up auth if provided
            auth = None
            if self.auth:
                auth = httpx.BasicAuth(self.auth[0], self.auth[1])

            response = await client.get(url, auth=auth)
            response.raise_for_status()

            # Parse HTML
            files = self._parse_directory_listing(
                response.text,
                url,
                directory_path,
            )

        logger.info(f"Found {len(files)} files in {directory_path}")
        return files

    def _parse_directory_listing(
        self,
        html: str,
        base_url: str,
        directory_path: str,
    ) -> List[RemoteFile]:
        """
        Parse Apache/nginx autoindex HTML to extract file links.

        Typical Apache autoindex format:
        <a href="filename.srt">filename.srt</a>  12-Jan-2025 14:30  45K

        Args:
            html: Raw HTML of directory listing
            base_url: URL of the directory (for resolving relative links)
            directory_path: Path for tracking

        Returns:
            List of RemoteFile objects
        """
        files: List[RemoteFile] = []
        soup = BeautifulSoup(html, 'html.parser')

        for link in soup.find_all('a'):
            href = link.get('href', '')
            if not href:
                continue

            # Skip parent directory and sorting links
            if href in ('..', '../', '?', '?C=N;O=D', '?C=M;O=A', '?C=S;O=A', '?C=D;O=A'):
                continue
            if href.startswith('?'):
                continue
            if href.endswith('/'):
                # This is a subdirectory - skip for now
                # (could recursively scan in future)
                continue

            # Determine file type by extension
            filename = href.split('/')[-1]
            ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

            if ext in self.TRANSCRIPT_EXTENSIONS:
                file_type = 'transcript'
            elif ext in self.SCREENGRAB_EXTENSIONS:
                file_type = 'screengrab'
            else:
                # Skip unknown file types
                continue

            # Build full URL
            full_url = urljoin(base_url + '/', href)

            # Extract Media ID from filename
            media_id = self._extract_media_id(filename)

            # Try to parse size/date from surrounding text
            file_size, modified_at = self._parse_file_metadata(link)

            files.append(RemoteFile(
                filename=filename,
                url=full_url,
                directory_path=directory_path,
                file_type=file_type,
                media_id=media_id,
                file_size_bytes=file_size,
                modified_at=modified_at,
            ))

        return files

    def _extract_media_id(self, filename: str) -> Optional[str]:
        """
        Extract Media ID from filename using PBS Wisconsin conventions.

        Examples:
            "2WLI1209HD_transcript.srt" -> "2WLI1209HD"
            "9UNP2005_screengrab.jpg" -> "9UNP2005"
            "WPT_2401_final.srt" -> None (doesn't match pattern)
        """
        match = self.MEDIA_ID_PATTERN.search(filename)
        if match:
            return match.group(1).upper()
        return None

    def _parse_file_metadata(self, link_element) -> tuple[Optional[int], Optional[datetime]]:
        """
        Try to parse file size and modification date from Apache autoindex listing.

        Apache format: <a>filename</a>  12-Jan-2025 14:30  45K

        Returns:
            (file_size_bytes, modified_at) tuple, with None for unparseable values
        """
        file_size = None
        modified_at = None

        # Get text after the link (siblings or parent text)
        try:
            next_text = link_element.next_sibling
            if next_text and isinstance(next_text, str):
                # Try to parse: "  12-Jan-2025 14:30  45K"
                parts = next_text.strip().split()

                # Parse date (format: DD-Mon-YYYY HH:MM)
                if len(parts) >= 2:
                    try:
                        date_str = f"{parts[0]} {parts[1]}"
                        modified_at = datetime.strptime(date_str, "%d-%b-%Y %H:%M")
                        modified_at = modified_at.replace(tzinfo=timezone.utc)
                    except (ValueError, IndexError):
                        pass

                # Parse size (format: 45K, 1.2M, etc.)
                if len(parts) >= 3:
                    size_str = parts[-1]
                    file_size = self._parse_size(size_str)

        except Exception:
            pass

        return file_size, modified_at

    def _parse_size(self, size_str: str) -> Optional[int]:
        """Parse human-readable size (45K, 1.2M, 500) to bytes."""
        try:
            size_str = size_str.strip().upper()
            if size_str.endswith('K'):
                return int(float(size_str[:-1]) * 1024)
            elif size_str.endswith('M'):
                return int(float(size_str[:-1]) * 1024 * 1024)
            elif size_str.endswith('G'):
                return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
            else:
                return int(size_str)
        except (ValueError, AttributeError):
            return None

    async def _track_file(self, remote_file: RemoteFile) -> bool:
        """
        Add file to available_files table if not already tracked.

        Args:
            remote_file: Discovered file info

        Returns:
            True if this is a new file, False if already tracked
        """
        async with get_session() as session:
            # Check if already tracked
            check_query = text("""
                SELECT id, status FROM available_files
                WHERE remote_url = :url
            """)
            result = await session.execute(check_query, {"url": remote_file.url})
            existing = result.fetchone()

            if existing:
                # Update last_seen_at
                update_query = text("""
                    UPDATE available_files
                    SET last_seen_at = :now
                    WHERE id = :id
                """)
                await session.execute(update_query, {
                    "now": datetime.now(timezone.utc).isoformat(),
                    "id": existing.id,
                })
                return False

            # Insert new file
            insert_query = text("""
                INSERT INTO available_files
                (remote_url, filename, directory_path, file_type, media_id,
                 file_size_bytes, remote_modified_at, first_seen_at, last_seen_at, status)
                VALUES
                (:remote_url, :filename, :directory_path, :file_type, :media_id,
                 :file_size_bytes, :remote_modified_at, :now, :now, 'new')
            """)

            now = datetime.now(timezone.utc).isoformat()
            await session.execute(insert_query, {
                "remote_url": remote_file.url,
                "filename": remote_file.filename,
                "directory_path": remote_file.directory_path,
                "file_type": remote_file.file_type,
                "media_id": remote_file.media_id,
                "file_size_bytes": remote_file.file_size_bytes,
                "remote_modified_at": remote_file.modified_at.isoformat() if remote_file.modified_at else None,
                "now": now,
            })

            logger.info(f"Tracked new {remote_file.file_type}: {remote_file.filename}")
            return True

    async def get_pending_screengrabs(self) -> List[dict]:
        """
        Get all 'new' screengrabs with Media IDs.

        Returns:
            List of file records ready for attachment
        """
        async with get_session() as session:
            query = text("""
                SELECT id, remote_url, filename, media_id, first_seen_at
                FROM available_files
                WHERE file_type = 'screengrab'
                  AND status = 'new'
                  AND media_id IS NOT NULL
                ORDER BY first_seen_at ASC
            """)
            result = await session.execute(query)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "remote_url": row.remote_url,
                    "filename": row.filename,
                    "media_id": row.media_id,
                    "first_seen_at": row.first_seen_at,
                }
                for row in rows
            ]


# Factory function
def get_ingest_scanner(
    base_url: str = "https://mmingest.pbswi.wisc.edu/",
    directories: Optional[List[str]] = None,
) -> IngestScanner:
    """Create IngestScanner instance with default config."""
    return IngestScanner(
        base_url=base_url,
        directories=directories or ["/"],
    )
