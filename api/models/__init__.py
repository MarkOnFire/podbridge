"""Pydantic Models - Sprint 2.1 + Sprint 11.1"""
from api.models.job import Job, JobCreate, JobUpdate, JobList, JobStatus, JobBase
from api.models.events import SessionEvent, EventCreate, EventData, EventType
from api.models.config import ConfigItem, ConfigCreate, ConfigUpdate, ConfigValueType
from api.models.ingest import (
    FileType,
    FileStatus,
    AvailableFile,
    AvailableFileCreate,
    AvailableFileWithSST,
    AvailableFilesResponse,
    ScreengrabAttachment,
    ScreengrabAttachmentCreate,
    RemoteFile,
    ScanResult,
    IngestConfig,
    IngestConfigUpdate,
    IngestConfigResponse,
    QueueFileResponse,
    BulkQueueRequest,
    BulkQueueResponse,
    AttachResult,
    BatchAttachResult,
    SSTRecordInfo,
)

__all__ = [
    # Job models
    "Job",
    "JobCreate",
    "JobUpdate",
    "JobList",
    "JobStatus",
    "JobBase",
    # Event models
    "SessionEvent",
    "EventCreate",
    "EventData",
    "EventType",
    # Config models
    "ConfigItem",
    "ConfigCreate",
    "ConfigUpdate",
    "ConfigValueType",
    # Ingest models (Sprint 11.1)
    "FileType",
    "FileStatus",
    "AvailableFile",
    "AvailableFileCreate",
    "AvailableFileWithSST",
    "AvailableFilesResponse",
    "ScreengrabAttachment",
    "ScreengrabAttachmentCreate",
    "RemoteFile",
    "ScanResult",
    "IngestConfig",
    "IngestConfigUpdate",
    "IngestConfigResponse",
    "QueueFileResponse",
    "BulkQueueRequest",
    "BulkQueueResponse",
    "AttachResult",
    "BatchAttachResult",
    "SSTRecordInfo",
]
