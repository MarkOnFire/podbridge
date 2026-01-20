# Feature Specification: Remote Ingest Server Watcher

## Overview

Automatically monitor the PBS Wisconsin media ingest server (`mmingest.pbswi.wisc.edu`) for new SRT transcript files and JPG screen grabs. Display newly available files in the dashboard with one-click queueing—without auto-processing.

**Goal**: Reduce manual file discovery friction while keeping human control over what gets processed.

## User Stories

> As a copy editor, I want to see newly available transcripts from the ingest server so I can quickly add them to the processing queue without manually downloading and uploading files.

> As a copy editor, I want JPG screen grabs to be automatically attached to their corresponding Airtable SST records so I don't have to manually upload them.

---

## Policy Exception: Airtable Write Access

**This feature requires a controlled exception to the READ-ONLY Airtable policy.**

The screengrab attachment feature will perform **additive-only writes** to Airtable:
- Only writes to the `Screen Grab` attachment field (`fldCCWjcowpE2wJhc`)
- **Never overwrites** existing attachments—only appends new ones
- Requires matching Media ID in filename to locate the correct SST record
- All writes are logged for audit trail

This exception is explicitly authorized by the project owner for this specific use case.

## Technical Requirements

### Server Details

- **URL**: `https://mmingest.pbswi.wisc.edu/`
- **Access Type**: Web directory listing (Apache/nginx autoindex)
- **File Types**:
  - `.srt` files (SubRip subtitle format) → Queue for transcript processing
  - `.jpg` / `.jpeg` files → Attach to SST Screen Grab field
- **Authentication**: TBD - may require basic auth or VPN access

### Architecture Components

```
┌─────────────────────────────────────┐
│  mmingest.pbswi.wisc.edu            │
│  (Web directory listing)            │
└─────────────────┬───────────────────┘
                  │ HTTP GET (polling)
                  ▼
┌─────────────────────────────────────┐
│  IngestScanner Service              │
│  api/services/ingest_scanner.py     │
│  - Fetch & parse directory HTML     │
│  - Extract .srt AND .jpg file links │
│  - Diff against known files         │
│  - Store new discoveries            │
│  - Route by file type               │
└─────────────────┬───────────────────┘
                  │
         ┌───────┴───────┐
         │               │
         ▼               ▼
┌─────────────────┐  ┌─────────────────┐
│  .srt files     │  │  .jpg files     │
│  (Transcripts)  │  │  (Screen Grabs) │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────────────┐
│ available_files │  │ ScreengrabAttacher      │
│ table (status:  │  │ api/services/           │
│ new/queued/etc) │  │   screengrab_attacher.py│
└────────┬────────┘  │ - Match Media ID → SST  │
         │           │ - Check existing grabs  │
         │           │ - Append (never replace)│
         │           │ - Log all attachments   │
         │           └────────────┬────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐  ┌─────────────────────────┐
│ Dashboard Panel │  │ Airtable SST            │
│ - [Add to Queue]│  │ Screen Grab field       │
│ - [Ignore]      │  │ (fldCCWjcowpE2wJhc)     │
└─────────────────┘  └─────────────────────────┘
```

---

## Database Schema

### New Table: `available_files`

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
    media_id TEXT,                         -- Extracted from filename if possible
    file_size_bytes INTEGER,               -- If available from listing
    remote_modified_at DATETIME,           -- If available from listing

    -- Tracking
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Status workflow
    status TEXT DEFAULT 'new',             -- new / queued / ignored / missing
    status_changed_at DATETIME,

    -- Linking (after action taken)
    job_id INTEGER REFERENCES jobs(id),    -- Link to job if queued (transcripts)
    airtable_record_id TEXT,               -- SST record if attached (screengrabs)
    attached_at DATETIME,                  -- When screengrab was attached

    -- Indexes for common queries
    UNIQUE(remote_url)
);

CREATE INDEX idx_available_files_status ON available_files(status);
CREATE INDEX idx_available_files_media_id ON available_files(media_id);
CREATE INDEX idx_available_files_first_seen ON available_files(first_seen_at);
CREATE INDEX idx_available_files_file_type ON available_files(file_type);
```

### Status Values

| Status | File Type | Description |
|--------|-----------|-------------|
| `new` | Both | File discovered, not yet acted upon |
| `queued` | Transcript | User clicked "Add to Queue", job created |
| `attached` | Screengrab | Successfully attached to SST record |
| `no_match` | Screengrab | Media ID could not be matched to SST record |
| `ignored` | Both | User explicitly dismissed this file |
| `missing` | Both | File was seen before but no longer on server |

---

## API Endpoints

### Router: `api/routers/ingest.py`

#### GET `/api/ingest/available`

List files available for queueing.

**Query Parameters:**
- `status` (optional): Filter by status (default: `new`)
- `limit` (optional): Max results (default: 50)
- `include_ignored` (optional): Include ignored files (default: false)

**Response:**
```json
{
  "files": [
    {
      "id": 1,
      "filename": "2WLI1215HD_transcript.srt",
      "remote_url": "https://mmingest.pbswi.wisc.edu/exports/2WLI1215HD_transcript.srt",
      "media_id": "2WLI1215HD",
      "first_seen_at": "2025-01-12T14:30:00Z",
      "status": "new",
      "file_size_bytes": 45000
    }
  ],
  "total_new": 5,
  "last_scan_at": "2025-01-12T15:00:00Z"
}
```

#### POST `/api/ingest/queue/{file_id}`

Download file from remote server and add to processing queue.

**Process:**
1. Fetch file from `remote_url`
2. Save to `transcripts/` folder
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

#### POST `/api/ingest/unignore/{file_id}`

Restore an ignored file to "new" status.

#### POST `/api/ingest/scan`

Trigger an immediate scan of the remote server.

**Response:**
```json
{
  "success": true,
  "new_files_found": 3,
  "total_files_on_server": 150,
  "scan_duration_ms": 1250
}
```

#### GET `/api/ingest/status`

Get scanner status and configuration.

**Response:**
```json
{
  "enabled": true,
  "server_url": "https://mmingest.pbswi.wisc.edu/",
  "poll_interval_minutes": 15,
  "last_scan_at": "2025-01-12T15:00:00Z",
  "last_scan_success": true,
  "files_by_status": {
    "new": 5,
    "queued": 42,
    "attached": 15,
    "no_match": 2,
    "ignored": 3
  }
}
```

### Screengrab-Specific Endpoints

#### GET `/api/ingest/screengrabs`

List discovered screengrab files and their attachment status.

**Query Parameters:**
- `status` (optional): Filter by status (`new`, `attached`, `no_match`, `ignored`)
- `limit` (optional): Max results (default: 50)

**Response:**
```json
{
  "screengrabs": [
    {
      "id": 42,
      "filename": "2WLI1215HD_screengrab.jpg",
      "remote_url": "https://mmingest.pbswi.wisc.edu/images/2WLI1215HD_screengrab.jpg",
      "media_id": "2WLI1215HD",
      "status": "new",
      "first_seen_at": "2025-01-12T14:30:00Z",
      "sst_record": {
        "id": "recXYZ123",
        "title": "Episode Title",
        "existing_screengrabs": 2
      }
    }
  ],
  "total_new": 3,
  "total_no_match": 1
}
```

#### POST `/api/ingest/screengrabs/{file_id}/attach`

Manually trigger attachment of a screengrab to its SST record.

**Process:**
1. Verify Media ID matches an SST record
2. Fetch current `Screen Grab` attachments from SST record
3. Download JPG from remote server
4. **Append** new attachment (preserve existing)
5. Update SST record via Airtable API
6. Update `available_files.status` to `attached`
7. Log the attachment action

**Response:**
```json
{
  "success": true,
  "sst_record_id": "recXYZ123",
  "attachment_count_before": 2,
  "attachment_count_after": 3,
  "message": "Screengrab attached successfully"
}
```

#### POST `/api/ingest/screengrabs/attach-all`

Attach all unattached screengrabs that have matching SST records.

**Response:**
```json
{
  "success": true,
  "attached": 5,
  "skipped_no_match": 2,
  "errors": []
}
```

#### POST `/api/ingest/screengrabs/{file_id}/retry-match`

Retry Media ID matching for a `no_match` screengrab (useful after manual SST record creation).

---

## Service: IngestScanner

### File: `api/services/ingest_scanner.py`

```python
class IngestScanner:
    """
    Monitors remote ingest server for new SRT files.

    Responsibilities:
    - Fetch and parse Apache/nginx directory listings
    - Extract file metadata (name, size, date if available)
    - Track files in database
    - Download files on demand for queueing
    """

    def __init__(self, config: IngestConfig):
        self.base_url = config.server_url
        self.poll_interval = config.poll_interval_minutes
        self.file_extensions = ['.srt', '.txt']  # Configurable

    async def scan_remote_server(self) -> ScanResult:
        """Fetch directory listing and update database."""

    async def download_file(self, file_id: int) -> Path:
        """Download a specific file to transcripts/ folder."""

    def parse_directory_listing(self, html: str) -> list[RemoteFile]:
        """Parse Apache/nginx autoindex HTML."""

    def extract_media_id(self, filename: str) -> Optional[str]:
        """Extract media ID from filename patterns."""
```

### HTML Parsing Strategy

Apache autoindex typically generates HTML like:
```html
<a href="2WLI1215HD_transcript.srt">2WLI1215HD_transcript.srt</a>  12-Jan-2025 14:30  45K
```

Use BeautifulSoup to:
1. Find all `<a>` tags with `.srt` or `.txt` href
2. Extract filename from href
3. Parse sibling text for date/size if available

### Configuration

Add to `config/ingest.json` or environment variables:

```json
{
  "ingest_server": {
    "enabled": true,
    "base_url": "https://mmingest.pbswi.wisc.edu/",
    "directories": ["/exports/", "/transcripts/", "/images/"],
    "poll_interval_minutes": 15,
    "transcript_extensions": [".srt", ".txt"],
    "screengrab_extensions": [".jpg", ".jpeg", ".png"],
    "auto_attach_screengrabs": true,
    "auth": {
      "type": "none",  // or "basic", "header"
      "username": "",
      "password": ""
    },
    "timeout_seconds": 30
  }
}
```

---

## Service: ScreengrabAttacher

### File: `api/services/screengrab_attacher.py`

```python
class ScreengrabAttacher:
    """
    Attaches screengrab images to Airtable SST records.

    SAFETY GUARANTEES:
    - ADDITIVE ONLY: Never removes or replaces existing attachments
    - AUDIT LOGGED: All attachment operations are logged
    - IDEMPOTENT: Re-running on same file won't duplicate attachments

    Responsibilities:
    - Match screengrab files to SST records by Media ID
    - Download images from remote server
    - Append to Airtable attachment field (never overwrite)
    - Track attachment history for audit trail
    """

    SST_TABLE_ID = "tblTKFOwTvK7xw1H5"
    SCREEN_GRAB_FIELD_ID = "fldCCWjcowpE2wJhc"

    async def attach_screengrab(self, file_id: int) -> AttachResult:
        """
        Attach a single screengrab to its matching SST record.

        Process:
        1. Get file record from database
        2. Look up SST record by Media ID
        3. Fetch current Screen Grab attachments
        4. Download image from remote URL
        5. Upload to Airtable (append to existing)
        6. Update local tracking record
        7. Log the operation
        """

    async def attach_all_pending(self) -> BatchAttachResult:
        """Attach all 'new' screengrabs that have matching SST records."""

    def _get_existing_attachments(self, record_id: str) -> list[dict]:
        """Fetch current Screen Grab attachments from SST record."""

    def _append_attachment(
        self,
        record_id: str,
        existing: list[dict],
        new_url: str,
        filename: str
    ) -> None:
        """
        Append new attachment to existing ones.

        CRITICAL: This method MUST preserve all existing attachments.
        The Airtable API replaces the entire field value, so we must:
        1. Fetch existing attachments
        2. Add new attachment to the list
        3. Send complete list back
        """

    def _is_duplicate(self, existing: list[dict], filename: str) -> bool:
        """Check if this exact filename is already attached."""
```

### Airtable Attachment Format

Airtable attachment fields expect this format:

```json
{
  "fields": {
    "Screen Grab": [
      // Existing attachments (MUST preserve these)
      {"id": "attXXX", "url": "https://..."},
      {"id": "attYYY", "url": "https://..."},
      // New attachment (append)
      {"url": "https://mmingest.pbswi.wisc.edu/images/2WLI1215HD.jpg"}
    ]
  }
}
```

**Important**: When updating, existing attachments are referenced by `id`. New attachments only need `url`—Airtable will download and store them.

### Logging & Audit Trail

All attachment operations are logged to `screengrab_attachments` table:

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
```

---

## Background Polling

### Option A: FastAPI Background Task

Add to worker startup:

```python
@app.on_event("startup")
async def start_ingest_scanner():
    if settings.ingest_enabled:
        asyncio.create_task(ingest_polling_loop())

async def ingest_polling_loop():
    scanner = IngestScanner(config)
    while True:
        try:
            await scanner.scan_remote_server()
        except Exception as e:
            logger.error(f"Ingest scan failed: {e}")
        await asyncio.sleep(config.poll_interval_minutes * 60)
```

### Option B: Separate Script (like watch_transcripts.py)

Create `watch_ingest_server.py` that runs independently and calls the API.

**Recommendation**: Option A for simplicity, integrated with existing API process.

---

## Web Dashboard Component

### New Component: `web/src/components/IngestPanel.tsx`

```tsx
interface IngestPanelProps {
  // Props
}

export function IngestPanel() {
  // State
  const [availableFiles, setAvailableFiles] = useState<RemoteFile[]>([]);
  const [lastScan, setLastScan] = useState<Date | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  // Actions
  const handleQueue = async (fileId: number) => { ... };
  const handleQueueAll = async () => { ... };
  const handleIgnore = async (fileId: number) => { ... };
  const handleManualScan = async () => { ... };

  return (
    <Card>
      <CardHeader>
        <h3>Available from Ingest Server</h3>
        <span>Last scan: {formatRelative(lastScan)}</span>
        <Button onClick={handleManualScan} disabled={isScanning}>
          {isScanning ? 'Scanning...' : 'Scan Now'}
        </Button>
      </CardHeader>

      <CardBody>
        {availableFiles.length === 0 ? (
          <EmptyState>No new files available</EmptyState>
        ) : (
          <>
            <Button onClick={handleQueueAll}>
              Queue All ({availableFiles.length})
            </Button>

            <FileList>
              {availableFiles.map(file => (
                <FileRow key={file.id}>
                  <span>{file.filename}</span>
                  <span>{file.media_id}</span>
                  <span>{formatRelative(file.first_seen_at)}</span>
                  <Button onClick={() => handleQueue(file.id)}>
                    Add to Queue
                  </Button>
                  <Button variant="ghost" onClick={() => handleIgnore(file.id)}>
                    Ignore
                  </Button>
                </FileRow>
              ))}
            </FileList>
          </>
        )}
      </CardBody>
    </Card>
  );
}
```

### Integration Points

- Add `IngestPanel` to Home page or dedicated "Ingest" page
- WebSocket updates when new files discovered
- Badge/notification for new file count

---

## Testing Requirements

### Unit Tests

- [ ] `test_ingest_scanner.py`
  - Directory HTML parsing (various Apache/nginx formats)
  - Media ID extraction from filenames
  - File type detection (.srt vs .jpg)
  - File status transitions

- [ ] `test_screengrab_attacher.py`
  - Attachment append logic (never overwrites)
  - Duplicate detection
  - No-match handling
  - Audit log creation

### Integration Tests

- [ ] `test_ingest_api.py`
  - Queue endpoint creates job correctly
  - Bulk queue operations
  - Ignore/unignore workflow
  - Scan endpoint returns correct counts

- [ ] `test_screengrab_api.py`
  - Attach endpoint adds to SST correctly
  - Existing attachments preserved
  - No-match returns appropriate error
  - Attach-all batch operation

### Manual Testing

- [ ] Verify actual connection to mmingest server
- [ ] Confirm file download works
- [ ] Test with various file naming conventions
- [ ] Verify SST linking works for downloaded files
- [ ] **Screengrab**: Verify attachment appears in Airtable
- [ ] **Screengrab**: Verify existing attachments NOT removed
- [ ] **Screengrab**: Verify duplicate attachment prevented

---

## Security Considerations

1. **URL Validation**: Only allow downloads from configured base URL
2. **File Size Limits**: Reject files over reasonable threshold (100MB)
3. **Rate Limiting**: Don't hammer the ingest server
4. **Credential Storage**: If auth needed, use environment variables, not config files

---

## Migration Plan

### Database Migration: `alembic/versions/XXX_add_available_files.py`

```python
def upgrade():
    op.create_table(
        'available_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('remote_url', sa.Text(), nullable=False, unique=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('directory_path', sa.Text()),
        sa.Column('media_id', sa.Text()),
        sa.Column('file_size_bytes', sa.Integer()),
        sa.Column('remote_modified_at', sa.DateTime()),
        sa.Column('first_seen_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('status', sa.Text(), server_default='new'),
        sa.Column('status_changed_at', sa.DateTime()),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id')),
    )
    op.create_index('idx_available_files_status', 'available_files', ['status'])
    op.create_index('idx_available_files_media_id', 'available_files', ['media_id'])

def downgrade():
    op.drop_table('available_files')
```

---

## Open Questions

1. **Authentication**: Does mmingest require any auth? VPN-only access?
2. **Directory Structure**: Is it flat or nested? Multiple directories to watch?
3. **File Naming**: What patterns are used? Can we reliably extract Media IDs?
4. **Cleanup**: Should we track when files disappear from the server?
5. **Notifications**: WebSocket push when new files found, or just poll from UI?

---

## Success Criteria

### Transcript Workflow
- [ ] Scanner successfully connects to mmingest server
- [ ] New .srt files appear in dashboard within polling interval
- [ ] One-click adds file to queue with correct Media ID linking
- [ ] Ignored files don't reappear
- [ ] No duplicate jobs created for same file
- [ ] Scan status visible in UI (last scan time, success/failure)

### Screengrab Workflow
- [ ] New .jpg files detected and tracked in database
- [ ] Media ID extracted correctly from filename
- [ ] SST record lookup finds correct record
- [ ] Attachment **appends** to existing screengrabs (never replaces)
- [ ] Duplicate filenames detected and skipped
- [ ] `no_match` status set when Media ID not found in SST
- [ ] Audit log captures all attachment operations
- [ ] Dashboard shows screengrab status and attachment counts
