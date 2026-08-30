"""Detection response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import DefectClass, SeverityBand


class DetectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_file_id: uuid.UUID
    defect_class: DefectClass
    confidence: float

    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float

    frame_index: int | None

    normalized_area: float | None
    class_weight: float | None
    severity_score: float | None
    severity_band: SeverityBand | None

    created_at: datetime


class DetectionRunResult(BaseModel):
    """Outcome of running inference over one media file."""

    media_file_id: uuid.UUID
    detection_count: int
    frames_analyzed: int
    model_weights: str
    detections: list[DetectionRead]


class InspectionDetectionRun(BaseModel):
    """Outcome of dispatching inference across an inspection."""

    inspection_id: uuid.UUID
    queued_media: int
    already_processed: int
    detail: str


class DefectClassCount(BaseModel):
    defect_class: DefectClass
    count: int


class SeverityBandCount(BaseModel):
    severity_band: SeverityBand
    count: int


class InspectionDetectionSummary(BaseModel):
    inspection_id: uuid.UUID
    media_total: int
    media_processed: int
    detection_total: int
    by_class: list[DefectClassCount]
    by_severity: list[SeverityBandCount] = []
    max_severity_score: float | None = None
    mean_severity_score: float | None = None


class RescoreResult(BaseModel):
    """Outcome of recomputing severity over stored detections."""

    rescored: int
    detail: str
