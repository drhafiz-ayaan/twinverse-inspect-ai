"""Media ingest — the Phase 1 upload path.

Accepts one or more images/videos against an inspection, streams each to
object storage, and records a row per file.

Per-file isolation is deliberate: one bad file in a batch of thirty drone
stills should not reject the other twenty-nine. Each file's outcome is
reported individually and the response carries accepted/rejected counts.
"""

import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import (
    get_inspection_or_404,
    get_media_file_or_404,
    require_inspector,
)
from app.db.models import Inspection, MediaFile
from app.db.session import get_db
from app.schemas.media import (
    MediaFileRead,
    MediaFileWithUrl,
    UploadResponse,
    UploadResult,
)
from app.services import media as media_svc
from app.services import storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["uploads"])

MAX_FILES_PER_REQUEST = 50


@router.post(
    "/inspections/{inspection_id}/uploads",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_media(
    response: Response,
    files: list[UploadFile] = File(..., description="One or more images or videos"),
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
    _: object = Depends(require_inspector),
) -> UploadResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="no files supplied"
        )
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"at most {MAX_FILES_PER_REQUEST} files per request",
        )

    storage.ensure_bucket()

    results: list[UploadResult] = []
    for upload in files:
        filename = upload.filename or "unnamed"
        try:
            record = _ingest_one(upload, inspection, db)
            results.append(
                UploadResult(
                    filename=filename,
                    accepted=True,
                    media_file=MediaFileRead.model_validate(record),
                )
            )
        except (
            media_svc.UnsupportedMediaType,
            media_svc.UploadTooLarge,
            ValueError,
        ) as exc:
            results.append(
                UploadResult(filename=filename, accepted=False, error=str(exc))
            )
        except storage.StorageError as exc:
            logger.exception("storage failure ingesting %s", filename)
            results.append(
                UploadResult(
                    filename=filename, accepted=False, error=f"storage error: {exc}"
                )
            )
        finally:
            upload.file.close()

    accepted = sum(1 for r in results if r.accepted)

    # Nothing usable in the batch is a client error, not a success.
    if accepted == 0:
        response.status_code = status.HTTP_400_BAD_REQUEST

    return UploadResponse(
        inspection_id=inspection.id,
        accepted_count=accepted,
        rejected_count=len(results) - accepted,
        results=results,
    )


def _ingest_one(
    upload: UploadFile, inspection: Inspection, db: Session
) -> MediaFile:
    """Validate, store, and record a single upload.

    Ordering matters: the object goes to the bucket first, then the row is
    committed. If the commit fails the object is deleted, so the bucket never
    accumulates files no row points at. The reverse order would risk a row
    referencing an object that was never written.
    """
    filename = upload.filename or "unnamed"
    media_type = media_svc.classify(upload.content_type or "")
    limit = media_svc.size_limit_for(media_type)

    spooled = media_svc.spool_to_temp(upload.file, limit)
    key = storage.build_object_key(inspection.id, filename)

    try:
        metadata = media_svc.probe(spooled.path, media_type)

        with open(spooled.path, "rb") as fh:
            storage.upload_fileobj(fh, key, upload.content_type or "application/octet-stream")
    finally:
        spooled.cleanup()

    record = MediaFile(
        inspection_id=inspection.id,
        storage_key=key,
        original_filename=filename[:512],
        content_type=(upload.content_type or "application/octet-stream")[:128],
        media_type=media_type,
        size_bytes=spooled.size_bytes,
        checksum_sha256=spooled.checksum_sha256,
        **metadata,
    )
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_object(key)
        raise
    db.refresh(record)
    return record


@router.get("/media/{media_id}", response_model=MediaFileWithUrl)
def get_media(media: MediaFile = Depends(get_media_file_or_404)) -> MediaFileWithUrl:
    return MediaFileWithUrl(
        **MediaFileRead.model_validate(media).model_dump(),
        download_url=storage.presigned_url(media.storage_key),
    )


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media: MediaFile = Depends(get_media_file_or_404),
    db: Session = Depends(get_db),
    _: object = Depends(require_inspector),
) -> None:
    """Removes the row and the stored object.

    Unlike the cascade delete on assets, an explicit single-file delete is an
    intentional act, so the object is reclaimed too.
    """
    key = media.storage_key
    db.delete(media)
    db.commit()
    storage.delete_object(key)
