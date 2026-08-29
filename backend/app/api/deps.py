"""Shared API dependencies."""

import uuid

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.db.models import Asset, Inspection, MediaFile
from app.db.session import get_db


def get_asset_or_404(
    asset_id: uuid.UUID = Path(...), db: Session = Depends(get_db)
) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"asset {asset_id} not found"
        )
    return asset


def get_inspection_or_404(
    inspection_id: uuid.UUID = Path(...), db: Session = Depends(get_db)
) -> Inspection:
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"inspection {inspection_id} not found",
        )
    return inspection


def get_media_file_or_404(
    media_id: uuid.UUID = Path(...), db: Session = Depends(get_db)
) -> MediaFile:
    media = db.get(MediaFile, media_id)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"media file {media_id} not found",
        )
    return media
