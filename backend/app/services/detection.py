"""Detection pipeline: object storage → inference → database rows.

Separated from `inference.py` so the model wrapper stays free of database and
storage concerns, and this orchestration can be tested against a stub detector.
"""

import logging
import os
import tempfile
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Detection, InspectionStatus, MediaFile
from app.services import inference, storage

logger = logging.getLogger(__name__)


def run_for_media(db: Session, media: MediaFile) -> tuple[list[Detection], int, str]:
    """Analyze one media file and replace its detection rows.

    Returns (rows, frames_analyzed, weights).

    Existing detections for the file are deleted first so re-running after a
    model upgrade replaces the results rather than accumulating two generations
    of boxes over the same image.
    """
    suffix = Path(media.original_filename).suffix or ""
    fd, tmp_name = tempfile.mkstemp(prefix="twinverse-infer-", suffix=suffix)
    os.close(fd)
    tmp_path = Path(tmp_name)

    try:
        storage.download_to_path(media.storage_key, str(tmp_path))
        result = inference.analyze(tmp_path, media.media_type)
    finally:
        tmp_path.unlink(missing_ok=True)

    db.execute(delete(Detection).where(Detection.media_file_id == media.id))

    rows: list[Detection] = []
    for raw in result.detections:
        x, y, w, h = raw.bbox
        rows.append(
            Detection(
                media_file_id=media.id,
                defect_class=raw.defect_class,
                confidence=raw.confidence,
                bbox_x=x,
                bbox_y=y,
                bbox_width=w,
                bbox_height=h,
                frame_index=raw.frame_index,
                # Geometry is free here. class_weight, severity_score and
                # severity_band are deliberately left null — the scoring engine
                # is Phase 3, and writing placeholder numbers now would make
                # unscored rows indistinguishable from scored ones.
                normalized_area=raw.normalized_area,
            )
        )

    db.add_all(rows)
    media.processed = True
    db.commit()
    for row in rows:
        db.refresh(row)

    weights = inference.active_detector().weights
    logger.info(
        "media %s: %d detections over %d frame(s) using %s",
        media.id,
        len(rows),
        result.frames_analyzed,
        weights,
    )
    return rows, result.frames_analyzed, weights


def run_for_inspection(
    db: Session, inspection_id, *, reprocess: bool = False
) -> tuple[int, int]:
    """Analyze every media file in an inspection.

    Returns (processed_count, skipped_count). Inspection status moves to
    PROCESSING for the duration and settles on COMPLETED or FAILED, so the
    dashboard can show progress rather than appearing to hang.
    """
    from app.db.models import Inspection

    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        return 0, 0

    stmt = select(MediaFile).where(MediaFile.inspection_id == inspection_id)
    if not reprocess:
        stmt = stmt.where(MediaFile.processed.is_(False))
    targets = list(db.scalars(stmt))

    inspection.status = InspectionStatus.PROCESSING
    db.commit()

    processed = 0
    failed = 0
    for media in targets:
        try:
            run_for_media(db, media)
            processed += 1
        except Exception:
            db.rollback()
            failed += 1
            logger.exception("inference failed for media %s", media.id)

    inspection = db.get(Inspection, inspection_id)
    if inspection is not None:
        # Any failure leaves the inspection FAILED rather than COMPLETED:
        # a partially analyzed inspection reported as complete would understate
        # the defect count, which is the dangerous direction to be wrong in.
        inspection.status = (
            InspectionStatus.FAILED if failed else InspectionStatus.COMPLETED
        )
        db.commit()

    return processed, failed
