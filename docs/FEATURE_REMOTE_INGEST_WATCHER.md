# Feature Specification: Remote Ingest Server Watcher

## Overview

Monitor the PBS Wisconsin media ingest server (`mmingest.pbswi.wisc.edu`) on a configurable schedule for SRT transcript files and JPG screen grabs that match QC-passed content in the Airtable SST. Display matches in a "Ready to Queue" screen for one-click processing.

**Goal**: Surface new content that's ready for editorial processing without manual file hunting.

## User Stories

> As a copy editor, I want to see transcripts that are ready for processing (content passed QC and file exists on ingest server) so I can quickly add them to the queue.

> As a copy editor, I want JPG screen grabs to be automatically attached to their corresponding Airtable SST records so I don't have to manually upload them.

---

## Design Decisions (Revised 2026-01-21)

### Trigger: Scheduled Scan (Not Continuous Polling)

**Why**: Content passes QC in Airtable, but files may not appear on the ingest server until hours or days later. A scheduled daily scan captures this naturally without complex state tracking.

**Configuration** (via web UI Settings page):
- **Scan interval**: Default 24 hours (midnight daily)
- **Enabled/Disabled toggle**: Can pause scanning
- **Manual scan button**: "Check Now" for immediate results

### Smart Scanning: QC-Passed Content Only

Instead of tracking every file on the server, we:
1. Query SST for content where `QC` = passed
2. For each, check if SRT/JPG exists on ingest server by Media ID
3. Only track files that match QC-passed content

This is more efficient and only surfaces actionable items.

### Server Access

- **URL**: `https://mmingest.pbswi.wisc.edu/`
- **Authentication**: None required (open for system-to-system transfers)
- **Structure**: Project directories + "misc" catch-all. Ignore "promos" folder.
- **File naming**: Media ID always at start of filename (e.g., `2WLI1215HD_transcript.srt`)

### File Handling

- **SRT files**: Copy to local `transcripts/` folder for safekeeping (server is regularly trimmed)
- **JPG files**: Download temporarily for Airtable upload, then clean up
- **Deletions**: Ignore - don't track when files disappear from server

---

## Policy Exception: Airtable Write Access

**This feature requires a controlled exception to the READ-ONLY Airtable policy.**

The screengrab attachment feature will perform **additive-only writes** to Airtable:
- Only writes to the `Screen Grab` attachment field (`fldCCWjcowpE2wJhc`)
- **Never overwrites** existing attachments—only appends new ones
- Requires matching Media ID in filename to locate the correct SST record
- All writes are logged for audit trail

This exception is explicitly authorized by the project owner for this specific use case.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Ingest Scanner System                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────────────────────────────┐  │
│  │    Scheduler     │     │              Scan Process                 │  │
│  │  (configurable)  │────▶│  1. Query SST for QC-passed Media IDs    │  │
│  │  Default: daily  │     │  2. Filter to those without existing jobs│  │
│  │  at midnight     │     │  3. For each, check ingest server        │  │
│  └──────────────────┘     │  4. Match files by Media ID prefix       │  │
│         ▲                 │  5. Copy SRTs to local transcripts/      │  │
│         │                 │  6. Store matches in available_files     │  │
│  ┌──────┴───────┐         │  7. Log screengrabs for later attachment │  │
│  │ Manual Scan  │         └──────────────────────────────────────────┘  │
│  │   Button     │                        │                              │
│  │ "Check Now"  │                        ▼                              │
│  └──────────────┘         ┌──────────────────────────────────────────┐  │
│                           │        "Ready to Queue" Screen            │  │
│  Settings (Web UI):       │  ┌────────────────────────────────────┐  │  │
│  • Interval (hours)       │  │ Media ID │ Title │ Project │ Status│  │  │
│  • Enabled (on/off)       │  │ 2WLI1215 │ Ep... │ WI Life │ Ready │  │  │
│  • Directories to scan    │  │ [Queue]  │       │         │       │  │  │
│                           │  └────────────────────────────────────┘  │  │
│                           │  [Queue All Selected]                     │  │
│                           └──────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Screengrab Attachment                          │   │
│  │  (Separate timing - screengrabs may arrive later than SRTs)       │   │
│  │  • Match JPGs to SST by Media ID                                  │   │
│  │  • Append to Screen Grab field (never replace)                    │   │
│  │  • Full audit trail                                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Table: `available_files`

```sql
CREATE TABLE available_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- File identification
    remote_url TEXT NOT NULL UNIQUE,      -- Full URL to the file
    filename TEXT NOT NULL,                -- Just the filename
    directory_path TEXT,                   -- Parent directory on server

    -- File type routing
    file_type TEXT NOT NULL,               -- 'transcript' or 'screengrab'

    -- Extracted metadata
    media_id TEXT,                         -- Extracted from filename
    file_size_bytes INTEGER,               -- If available from listing
    remote_modified_at DATETIME,           -- If available from listing

    -- Tracking
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Status workflow
    status TEXT DEFAULT 'new',             -- new / queued / ignored / attached / no_match
    status_changed_at DATETIME,

    -- Linking (after action taken)
    job_id INTEGER REFERENCES jobs(id),    -- Link to job if queued (transcripts)
    airtable_record_id TEXT,               -- SST record if attached (screengrabs)
    attached_at DATETIME,                  -- When screengrab was attached

    UNIQUE(remote_url)
);

CREATE INDEX idx_available_files_status ON available_files(status);
CREATE INDEX idx_available_files_media_id ON available_files(media_id);
CREATE INDEX idx_available_files_first_seen ON available_files(first_seen_at);
CREATE INDEX idx_available_files_file_type ON available_files(file_type);
```

### Table: `screengrab_attachments` (Audit Log)

```sql
CREATE TABLE screengrab_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    available_file_id INTEGER REFERENCES available_files(id),
    sst_record_id TEXT NOT NULL,
    media_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    remote_url TEXT NOT NULL,
    attached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    attachments_before INTEGER,
    attachments_after INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX idx_screengrab_attachments_sst ON screengrab_attachments(sst_record_id);
CREATE INDEX idx_screengrab_attachments_date ON screengrab_attachments(attached_at);
```

### Table: `ingest_config` (Runtime Settings)

```sql
CREATE TABLE ingest_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default values inserted on first run:
-- scan_interval_hours: 24
-- scan_enabled: true
-- last_scan_at: null
-- scan_time: "00:00" (midnight)
```

### Status Values

| Status | File Type | Description |
|--------|-----------|-------------|
| `new` | Both | File discovered, ready to queue/attach |
| `queued` | Transcript | User clicked "Add to Queue", job created |
| `attached` | Screengrab | Successfully attached to SST record |
| `no_match` | Screengrab | Media ID could not be matched to SST record |
| `ignored` | Both | User explicitly dismissed this file |

---

## API Endpoints

### Router: `api/routers/ingest.py`

#### GET `/api/ingest/available`

List files available for queueing.

**Query Parameters:**
- `status` (optional): Filter by status (default: `new`)
- `file_type` (optional): Filter by type (`transcript` or `screengrab`)
- `limit` (optional): Max results (default: 50)

**Response:**
```json
{
  "files": [
    {
      "id": 1,
      "filename": "2WLI1215HD_transcript.srt",
      "media_id": "2WLI1215HD",
      "file_type": "transcript",
      "first_seen_at": "2025-01-12T00:00:00Z",
      "status": "new",
      "sst_record": {
        "id": "recXYZ123",
        "title": "Episode Title",
        "project": "Wisconsin Life"
      }
    }
  ],
  "total_new": 5,
  "last_scan_at": "2025-01-12T00:00:00Z"
}
```

#### POST `/api/ingest/queue/{file_id}`

Add a discovered file to the processing queue.

**Process:**
1. Verify file exists in `available_files` with status `new`
2. If not already local, download from `remote_url` to `transcripts/`
3. Create job via existing queue logic (with SST linking)
4. Update `available_files.status` to `queued`
5. Link `available_files.job_id` to new job

**Response:**
```json
{
  "success": true,
  "job_id": 42,
  "message": "File queued successfully"
}
```

#### POST `/api/ingest/queue/bulk`

Queue multiple files at once.

**Request Body:**
```json
{
  "file_ids": [1, 2, 3]
}
```

#### POST `/api/ingest/ignore/{file_id}`

Mark a file as ignored (won't show in "new" list).

#### POST `/api/ingest/scan`

Trigger an immediate scan (the "Check Now" button).

**Response:**
```json
{
  "success": true,
  "qc_passed_checked": 25,
  "new_transcripts_found": 3,
  "new_screengrabs_found": 2,
  "scan_duration_ms": 1250
}
```

#### GET `/api/ingest/config`

Get current scanner configuration.

**Response:**
```json
{
  "enabled": true,
  "scan_interval_hours": 24,
  "scan_time": "00:00",
  "last_scan_at": "2025-01-12T00:00:00Z",
  "last_scan_success": true,
  "server_url": "https://mmingest.pbswi.wisc.edu/",
  "directories": ["/exports/", "/misc/"]
}
```

#### PUT `/api/ingest/config`

Update scanner configuration (from Settings page).

**Request Body:**
```json
{
  "enabled": true,
  "scan_interval_hours": 24,
  "scan_time": "00:00"
}
```

### Screengrab-Specific Endpoints

#### GET `/api/ingest/screengrabs`

List discovered screengrab files and their attachment status.

#### POST `/api/ingest/screengrabs/{file_id}/attach`

Manually trigger attachment of a screengrab to its SST record.

#### POST `/api/ingest/screengrabs/attach-all`

Attach all unattached screengrabs that have matching SST records.

---

## Services

### IngestScanner (`api/services/ingest_scanner.py`)

```python
class IngestScanner:
    """
    Scans ingest server for files matching QC-passed content.

    Key difference from original design: We don't track every file.
    We query SST first, then look for matching files.
    """

    async def run_scan(self) -> ScanResult:
        """
        Main scan process:
        1. Query SST for QC-passed records without jobs
        2. For each Media ID, check ingest server
        3. Store matches in available_files
        """

    async def get_qc_passed_media_ids(self) -> list[str]:
        """Query Airtable SST for QC-passed Media IDs."""

    async def check_ingest_server(self, media_id: str) -> list[RemoteFile]:
        """Check if files for this Media ID exist on server."""

    async def download_file(self, file_id: int) -> Path:
        """Download a file to local transcripts/ folder."""

    def parse_directory_listing(self, html: str) -> list[RemoteFile]:
        """Parse Apache/nginx autoindex HTML."""
```

### ScreengrabAttacher (`api/services/screengrab_attacher.py`)

```python
class ScreengrabAttacher:
    """
    Attaches screengrab images to Airtable SST records.

    SAFETY GUARANTEES:
    - ADDITIVE ONLY: Never removes or replaces existing attachments
    - AUDIT LOGGED: All operations logged to screengrab_attachments
    - IDEMPOTENT: Duplicate filenames detected and skipped
    """

    SST_TABLE_ID = "tblTKFOwTvK7xw1H5"
    SCREEN_GRAB_FIELD_ID = "fldCCWjcowpE2wJhc"

    async def attach_screengrab(self, file_id: int) -> AttachResult:
        """Attach a single screengrab to its matching SST record."""

    async def attach_all_pending(self) -> BatchAttachResult:
        """Attach all 'new' screengrabs with matching SST records."""
```

---

## Configuration

### Default Configuration (`config/llm-config.json`)

```json
{
  "ingest_server": {
    "enabled": true,
    "base_url": "https://mmingest.pbswi.wisc.edu/",
    "directories": ["/exports/", "/misc/"],
    "ignore_directories": ["/promos/"],
    "transcript_extensions": [".srt", ".txt"],
    "screengrab_extensions": [".jpg", ".jpeg", ".png"],
    "scan_interval_hours": 24,
    "scan_time": "00:00",
    "timeout_seconds": 30,
    "max_file_size_mb": 100
  }
}
```

### Runtime Settings (Stored in Database)

These can be changed via the web UI Settings page:
- `scan_interval_hours`: How often to scan (default: 24)
- `scan_time`: What time to run daily scan (default: "00:00")
- `enabled`: Whether scheduled scanning is active

---

## Web Dashboard Components

### Ready to Queue Panel (`web/src/components/IngestPanel.tsx`)

Shows on Home page when there are items ready to process:

```
┌─────────────────────────────────────────────────────────────────┐
│ Ready to Queue                                    [Check Now]   │
├─────────────────────────────────────────────────────────────────┤
│ Last scan: 6 hours ago • Next scan: in 18 hours                 │
├─────────────────────────────────────────────────────────────────┤
│ ☐ 2WLI1215HD │ Candle Making Workshop │ WI Life    │ [Queue]   │
│ ☐ 9UNP2005HD │ Lecture on Economics   │ UPlace     │ [Queue]   │
│ ☐ 2WLI1216HD │ Historic Barns         │ WI Life    │ [Queue]   │
├─────────────────────────────────────────────────────────────────┤
│ [Queue Selected (0)]                              [Ignore All]  │
└─────────────────────────────────────────────────────────────────┘
```

### Screengrab Panel (`web/src/components/ScreengrabPanel.tsx`)

Shows pending screengrab attachments:

```
┌─────────────────────────────────────────────────────────────────┐
│ Screengrabs                                    [Attach All (3)] │
├─────────────────────────────────────────────────────────────────┤
│ 2WLI1215HD.jpg │ WI Life Ep 1215 │ 2 existing │ [Attach]       │
│ 9UNP2005HD.jpg │ Economics Lect. │ 0 existing │ [Attach]       │
│ UNKNOWN123.jpg │ No SST match    │ --         │ [Ignore]       │
└─────────────────────────────────────────────────────────────────┘
```

### Settings Page Addition

Add to Settings page:

```
┌─────────────────────────────────────────────────────────────────┐
│ Ingest Scanner Settings                                         │
├─────────────────────────────────────────────────────────────────┤
│ Enabled: [✓]                                                    │
│ Scan interval: [24] hours                                       │
│ Scan time: [00:00]                                              │
│ Server URL: https://mmingest.pbswi.wisc.edu/ (read-only)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scheduling Implementation

### Option: APScheduler (Recommended)

Use APScheduler for reliable scheduled tasks:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    # Load config from database
    config = await get_ingest_config()
    if config.enabled:
        hour, minute = config.scan_time.split(":")
        scheduler.add_job(
            run_ingest_scan,
            CronTrigger(hour=int(hour), minute=int(minute)),
            id="ingest_scan"
        )
        scheduler.start()

async def update_scan_schedule(new_config: IngestConfig):
    """Called when user updates settings."""
    scheduler.remove_job("ingest_scan")
    if new_config.enabled:
        # Re-add with new schedule
        ...
```

---

## Success Criteria

### Transcript Workflow
- [ ] Scheduled scan runs at configured time
- [ ] Manual "Check Now" triggers immediate scan
- [ ] Only QC-passed content with matching files shown
- [ ] One-click queues file with correct SST linking
- [ ] SRT files copied locally for safekeeping
- [ ] Settings page allows interval/time configuration

### Screengrab Workflow
- [ ] JPG files detected during scan
- [ ] SST record matched by Media ID
- [ ] Attachment **appends** to existing (never replaces)
- [ ] Duplicate filenames detected and skipped
- [ ] `no_match` shown separately with explanation
- [ ] Full audit trail in database

---

## Simplified Task Breakdown

### Phase 1: Foundation (4 tasks)
1. Database migration (available_files, screengrab_attachments, ingest_config)
2. Pydantic models for ingest types
3. Configuration schema and defaults
4. APScheduler integration

### Phase 2: Core Scanner (3 tasks)
5. IngestScanner: SST query for QC-passed Media IDs
6. IngestScanner: Directory listing parser and file matching
7. IngestScanner: File download to local transcripts/

### Phase 3: API Layer (3 tasks)
8. Ingest router: Read endpoints (available, config, screengrabs)
9. Ingest router: Action endpoints (queue, ignore, scan, attach)
10. Config update endpoint for Settings page

### Phase 4: Frontend (3 tasks)
11. IngestPanel component (Ready to Queue)
12. ScreengrabPanel component
13. Settings page ingest section

### Phase 5: Testing (2 tasks)
14. Unit tests (HTML parsing, Media ID extraction)
15. Integration tests (API endpoints, SST queries)

**Total: 15 tasks** (reduced from 21)
