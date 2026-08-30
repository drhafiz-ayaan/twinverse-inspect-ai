"""S3-compatible object storage.

Targets MinIO locally. Because everything here goes through the S3 API, moving
to Alibaba Cloud OSS or AWS S3 is a configuration change (`S3_ENDPOINT_URL`,
keys, bucket) rather than a code change — see the README's cloud note.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

# ClientError covers responses the endpoint actually returned. BotoCoreError
# covers never reaching it at all — DNS failure, refused connection, timeout.
# Catching only the first lets a connection error escape as an unhandled
# exception, which killed API startup under Compose before MinIO was accepting
# S3 calls.
STORAGE_ERRORS = (ClientError, BotoCoreError)

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Raised when the object store cannot satisfy a request."""


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(bucket: str | None = None) -> None:
    """Create the bucket if it does not already exist. Idempotent."""
    bucket = bucket or settings.s3_bucket
    client = get_client()
    try:
        client.head_bucket(Bucket=bucket)
        return
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise StorageError(f"cannot reach bucket {bucket!r}: {exc}") from exc
    except BotoCoreError as exc:
        raise StorageError(f"cannot reach object storage: {exc}") from exc

    try:
        client.create_bucket(Bucket=bucket)
        logger.info("created bucket %s", bucket)
    except ClientError as exc:
        # A concurrent process may have won the race; that is fine.
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise StorageError(f"cannot create bucket {bucket!r}: {exc}") from exc
    except BotoCoreError as exc:
        raise StorageError(f"cannot create bucket {bucket!r}: {exc}") from exc


def build_object_key(inspection_id: uuid.UUID, filename: str) -> str:
    """Date-partitioned, collision-free key.

    The random suffix means two uploads of the same filename to the same
    inspection cannot overwrite each other.
    """
    stamp = datetime.now(timezone.utc)
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    return (
        f"inspections/{inspection_id}/"
        f"{stamp:%Y/%m/%d}/{uuid.uuid4().hex}{suffix}"
    )


def upload_fileobj(fileobj: BinaryIO, key: str, content_type: str,
                   bucket: str | None = None) -> None:
    """Stream an open file object into the bucket.

    Uses `upload_fileobj`, which chunks internally, so a 500 MB video never has
    to be held in memory.
    """
    bucket = bucket or settings.s3_bucket
    try:
        get_client().upload_fileobj(
            fileobj, bucket, key, ExtraArgs={"ContentType": content_type}
        )
    except STORAGE_ERRORS as exc:
        raise StorageError(f"upload of {key!r} failed: {exc}") from exc


def download_to_path(key: str, destination: str, bucket: str | None = None) -> None:
    """Fetch an object to a local path.

    Inference needs a real file on disk — OpenCV's video decoder seeks, so a
    streaming body is not enough.
    """
    bucket = bucket or settings.s3_bucket
    try:
        get_client().download_file(bucket, key, destination)
    except STORAGE_ERRORS as exc:
        raise StorageError(f"download of {key!r} failed: {exc}") from exc


def delete_object(key: str, bucket: str | None = None) -> None:
    """Best-effort delete, used to roll back a failed upload transaction."""
    bucket = bucket or settings.s3_bucket
    try:
        get_client().delete_object(Bucket=bucket, Key=key)
    except STORAGE_ERRORS:
        logger.warning("could not delete orphaned object %s", key, exc_info=True)


def presigned_url(key: str, expires_in: int | None = None,
                  bucket: str | None = None) -> str:
    bucket = bucket or settings.s3_bucket
    expires_in = expires_in or settings.presign_expiry_seconds
    try:
        return get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except STORAGE_ERRORS as exc:
        raise StorageError(f"cannot presign {key!r}: {exc}") from exc
