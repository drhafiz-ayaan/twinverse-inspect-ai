"""Media intake: spooling uploads to disk, hashing, and metadata probing."""

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.db.models import MediaType

logger = logging.getLogger(__name__)

# Read in 1 MiB blocks: large enough to keep syscall overhead down, small
# enough that memory use stays flat regardless of upload size.
CHUNK_SIZE = 1024 * 1024


class UploadTooLarge(ValueError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"file exceeds the {limit} byte limit")
        self.limit = limit


class UnsupportedMediaType(ValueError):
    pass


@dataclass(slots=True)
class SpooledUpload:
    path: Path
    size_bytes: int
    checksum_sha256: str

    def cleanup(self) -> None:
        try:
            os.unlink(self.path)
        except OSError:
            logger.warning("could not remove temp file %s", self.path, exc_info=True)


def classify(content_type: str) -> MediaType:
    """Map a MIME type onto image/video, rejecting anything not allowlisted."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in settings.allowed_image_types:
        return MediaType.IMAGE
    if ct in settings.allowed_video_types:
        return MediaType.VIDEO
    raise UnsupportedMediaType(
        f"content type {ct!r} is not accepted; allowed: "
        + ", ".join(settings.allowed_content_types)
    )


def size_limit_for(media_type: MediaType) -> int:
    return (
        settings.max_image_bytes
        if media_type is MediaType.IMAGE
        else settings.max_video_bytes
    )


def spool_to_temp(source: BinaryIO, max_bytes: int) -> SpooledUpload:
    """Stream an upload to a temp file, hashing as we go.

    The limit is enforced against bytes actually read rather than a
    client-supplied Content-Length header, so an oversized or lying request is
    cut off instead of filling the disk. Writing to disk (rather than straight
    through to S3) is what lets us probe dimensions and compute a checksum
    before committing anything.
    """
    digest = hashlib.sha256()
    total = 0
    fd, tmp_name = tempfile.mkstemp(prefix="twinverse-upload-")
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "wb") as tmp:
            while chunk := source.read(CHUNK_SIZE):
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLarge(max_bytes)
                digest.update(chunk)
                tmp.write(chunk)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    if total == 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("uploaded file is empty")

    return SpooledUpload(tmp_path, total, digest.hexdigest())


def probe_image(path: Path) -> dict[str, object]:
    """Best-effort image dimensions.

    Probing failures are logged and swallowed: an unreadable file is still
    stored, just without metadata. Rejecting it here would lose the upload.
    """
    try:
        from PIL import Image

        with Image.open(path) as img:
            return {"width": img.width, "height": img.height}
    except Exception:
        logger.warning("could not probe image %s", path, exc_info=True)
        return {}


def probe_video(path: Path) -> dict[str, object]:
    """Best-effort video dimensions, duration and frame count."""
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            logger.warning("could not open video %s", path)
            return {}
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        finally:
            cap.release()

        meta: dict[str, object] = {}
        if width > 0:
            meta["width"] = width
        if height > 0:
            meta["height"] = height
        if frames > 0:
            meta["frame_count"] = frames
        if fps > 0:
            meta["fps"] = round(fps, 3)
            if frames > 0:
                meta["duration_seconds"] = round(frames / fps, 3)
        return meta
    except Exception:
        logger.warning("could not probe video %s", path, exc_info=True)
        return {}


def probe(path: Path, media_type: MediaType) -> dict[str, object]:
    return (
        probe_image(path) if media_type is MediaType.IMAGE else probe_video(path)
    )
