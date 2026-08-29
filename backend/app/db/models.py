"""ORM models: assets, inspections, media files, detections.

Detection rows are written by the Phase 2 inference service; the table and its
severity columns are defined here so the schema lands in one migration rather
than being bolted on later.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Store enum *values* (not member names) in a native PostgreSQL enum."""
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda e: [member.value for member in e],
    )


class AssetType(str, enum.Enum):
    BRIDGE = "bridge"
    BUILDING = "building"
    ROAD = "road"
    DAM = "dam"
    PIPELINE = "pipeline"
    TUNNEL = "tunnel"
    OTHER = "other"


class InspectionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class DefectClass(str, enum.Enum):
    CRACK = "crack"
    CORROSION = "corrosion"
    SURFACE_DAMAGE = "surface_damage"
    MISSING_COMPONENT = "missing_component"


class SeverityBand(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        _pg_enum(AssetType, "asset_type"), nullable=False, default=AssetType.OTHER
    )
    location: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)

    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="ck_asset_latitude"
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude BETWEEN -180 AND 180)",
            name="ck_asset_longitude",
        ),
        Index("ix_assets_asset_type", "asset_type"),
    )


class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[InspectionStatus] = mapped_column(
        _pg_enum(InspectionStatus, "inspection_status"),
        nullable=False,
        default=InspectionStatus.PENDING,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    asset: Mapped["Asset"] = relationship(back_populates="inspections")
    media_files: Mapped[list["MediaFile"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_inspections_asset_id", "asset_id"),
        Index("ix_inspections_status", "status"),
    )


class MediaFile(Base, TimestampMixin):
    __tablename__ = "media_files"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Object key in the S3-compatible bucket. Unique so a retry cannot silently
    # orphan the previous object.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(
        _pg_enum(MediaType, "media_type"), nullable=False
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # Probed metadata. Nullable because probing is best-effort: an unreadable
    # file is still stored, just without dimensions.
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    frame_count: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)

    # Flipped by the Phase 2 inference pass.
    processed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )

    inspection: Mapped["Inspection"] = relationship(back_populates="media_files")
    detections: Mapped[list["Detection"]] = relationship(
        back_populates="media_file", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_media_size_positive"),
        Index("ix_media_files_inspection_id", "inspection_id"),
        Index("ix_media_files_processed", "processed"),
    )


class Detection(Base, TimestampMixin):
    """A single detected defect.

    Bounding boxes are stored **normalized** to 0..1 against the source frame,
    so they survive resizing and can be overlaid on any rendition without
    carrying the original pixel dimensions around.
    """

    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_file_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="CASCADE"),
        nullable=False,
    )

    defect_class: Mapped[DefectClass] = mapped_column(
        _pg_enum(DefectClass, "defect_class"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    # Null for stills; frame index into the source video otherwise.
    frame_index: Mapped[int | None] = mapped_column(Integer)

    # Severity inputs kept alongside the result so the score shown in the UI can
    # be re-derived and explained rather than taken on trust (README D-004).
    normalized_area: Mapped[float | None] = mapped_column(Float)
    class_weight: Mapped[float | None] = mapped_column(Float)
    severity_score: Mapped[float | None] = mapped_column(Float)
    severity_band: Mapped[SeverityBand | None] = mapped_column(
        _pg_enum(SeverityBand, "severity_band")
    )

    media_file: Mapped["MediaFile"] = relationship(back_populates="detections")

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_detection_confidence"
        ),
        CheckConstraint(
            "bbox_x >= 0 AND bbox_y >= 0 AND bbox_width > 0 AND bbox_height > 0",
            name="ck_detection_bbox_positive",
        ),
        Index("ix_detections_media_file_id", "media_file_id"),
        Index("ix_detections_defect_class", "defect_class"),
        Index("ix_detections_severity_band", "severity_band"),
    )
