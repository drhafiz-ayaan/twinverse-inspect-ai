"""Detection endpoints — run inference and read the results."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_inspection_or_404, get_media_file_or_404
from app.core.config import settings
from app.db.models import DefectClass, Detection, Inspection, MediaFile
from app.db.session import SessionLocal, get_db
from app.schemas.detection import (
    DefectClassCount,
    DetectionRead,
    DetectionRunResult,
    InspectionDetectionRun,
    InspectionDetectionSummary,
)
from app.services import detection as detection_svc
from app.services import inference, storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["detections"])


@router.post("/media/{media_id}/detect", response_model=DetectionRunResult)
def detect_media(
    media: MediaFile = Depends(get_media_file_or_404), db: Session = Depends(get_db)
) -> DetectionRunResult:
    """Run inference on one media file and return the detections.

    Synchronous: a single image is fast enough to answer in-request, and the
    immediate feedback is worth more than the concurrency during a demo. Whole
    inspections go through the background endpoint below.
    """
    try:
        rows, frames, weights = detection_svc.run_for_media(db, media)
    except storage.StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("inference failed for media %s", media.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"inference failed: {exc}",
        ) from exc

    return DetectionRunResult(
        media_file_id=media.id,
        detection_count=len(rows),
        frames_analyzed=frames,
        model_weights=weights,
        detections=[DetectionRead.model_validate(r) for r in rows],
    )


@router.get("/media/{media_id}/detections", response_model=list[DetectionRead])
def list_media_detections(
    media: MediaFile = Depends(get_media_file_or_404), db: Session = Depends(get_db)
) -> list[Detection]:
    stmt = (
        select(Detection)
        .where(Detection.media_file_id == media.id)
        .order_by(Detection.confidence.desc())
    )
    return list(db.scalars(stmt))


def _run_inspection_job(inspection_id: uuid.UUID, reprocess: bool) -> None:
    """Background worker. Owns its session — the request's is already closed."""
    db = SessionLocal()
    try:
        detection_svc.run_for_inspection(db, inspection_id, reprocess=reprocess)
    except Exception:
        logger.exception("inspection detection job failed for %s", inspection_id)
    finally:
        db.close()


@router.post(
    "/inspections/{inspection_id}/detect",
    response_model=InspectionDetectionRun,
    status_code=status.HTTP_202_ACCEPTED,
)
def detect_inspection(
    background: BackgroundTasks,
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
    reprocess: bool = Query(
        default=False,
        description="Re-analyze media already marked processed",
    ),
) -> InspectionDetectionRun:
    """Dispatch inference across an inspection's media.

    Returns 202 immediately; poll the inspection's `status` field, which moves
    PENDING → PROCESSING → COMPLETED (or FAILED).

    A `BackgroundTasks` job runs in the same process, which is fine for a demo
    but does not survive a restart. Phase 6 should move this to a real queue.
    """
    stmt = select(func.count(MediaFile.id)).where(
        MediaFile.inspection_id == inspection.id
    )
    total = db.scalar(stmt) or 0
    done = (
        db.scalar(stmt.where(MediaFile.processed.is_(True)))
        if total
        else 0
    ) or 0
    queued = total if reprocess else total - done

    if queued == 0:
        return InspectionDetectionRun(
            inspection_id=inspection.id,
            queued_media=0,
            already_processed=done,
            detail=(
                "nothing to do: no media uploaded"
                if total == 0
                else "all media already processed; pass reprocess=true to re-run"
            ),
        )

    background.add_task(_run_inspection_job, inspection.id, reprocess)
    return InspectionDetectionRun(
        inspection_id=inspection.id,
        queued_media=queued,
        already_processed=done,
        detail="inference dispatched; poll the inspection status",
    )


@router.get(
    "/inspections/{inspection_id}/detections", response_model=list[DetectionRead]
)
def list_inspection_detections(
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
) -> list[Detection]:
    stmt = (
        select(Detection)
        .join(MediaFile, MediaFile.id == Detection.media_file_id)
        .where(MediaFile.inspection_id == inspection.id)
        .order_by(Detection.confidence.desc())
    )
    return list(db.scalars(stmt))


@router.get(
    "/inspections/{inspection_id}/detections/summary",
    response_model=InspectionDetectionSummary,
)
def inspection_detection_summary(
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
) -> InspectionDetectionSummary:
    """Counts for the dashboard: media processed, and detections by class."""
    media_total = (
        db.scalar(
            select(func.count(MediaFile.id)).where(
                MediaFile.inspection_id == inspection.id
            )
        )
        or 0
    )
    media_processed = (
        db.scalar(
            select(func.count(MediaFile.id)).where(
                MediaFile.inspection_id == inspection.id,
                MediaFile.processed.is_(True),
            )
        )
        or 0
    )

    rows = db.execute(
        select(Detection.defect_class, func.count(Detection.id))
        .join(MediaFile, MediaFile.id == Detection.media_file_id)
        .where(MediaFile.inspection_id == inspection.id)
        .group_by(Detection.defect_class)
        .order_by(func.count(Detection.id).desc())
    ).all()

    return InspectionDetectionSummary(
        inspection_id=inspection.id,
        media_total=media_total,
        media_processed=media_processed,
        detection_total=sum(count for _, count in rows),
        by_class=[
            DefectClassCount(defect_class=cls, count=count) for cls, count in rows
        ],
    )


@router.get("/detector", tags=["detections"])
def detector_info() -> dict[str, object]:
    """What model is actually loaded.

    Exposed because "which weights produced these boxes" is the first question
    anyone asks of a detection, and guessing from config is not good enough.
    """
    return {
        "weights": inference.active_detector().weights,
        "confidence_threshold": settings.confidence_threshold,
        "video_frame_stride": settings.video_frame_stride,
        "video_max_frames": settings.video_max_frames,
        "defect_classes": [c.value for c in DefectClass],
    }
