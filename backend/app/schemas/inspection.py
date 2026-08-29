"""Inspection request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import InspectionStatus


class InspectionCreate(BaseModel):
    asset_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    notes: str | None = None
    inspected_at: datetime | None = None


class InspectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: InspectionStatus | None = None
    notes: str | None = None
    inspected_at: datetime | None = None


class InspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    title: str
    status: InspectionStatus
    notes: str | None
    inspected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InspectionWithMedia(InspectionRead):
    media_count: int = 0
