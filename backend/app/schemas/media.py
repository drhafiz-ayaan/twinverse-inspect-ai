"""Media file response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import MediaType


class MediaFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    storage_key: str
    original_filename: str
    content_type: str
    media_type: MediaType
    size_bytes: int
    checksum_sha256: str
    width: int | None
    height: int | None
    duration_seconds: float | None
    frame_count: int | None
    fps: float | None
    processed: bool
    created_at: datetime


class MediaFileWithUrl(MediaFileRead):
    """A media file plus a time-limited download link.

    The URL is generated per request rather than stored, so it cannot go stale
    in the database.
    """

    download_url: str


class UploadResult(BaseModel):
    """Outcome of a single file within a multi-file upload."""

    filename: str
    accepted: bool
    media_file: MediaFileRead | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    inspection_id: uuid.UUID
    accepted_count: int
    rejected_count: int
    results: list[UploadResult]
