"""Inspection CRUD and media listing."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_inspection_or_404
from app.db.models import Asset, Inspection, InspectionStatus, MediaFile
from app.db.session import get_db
from app.schemas.inspection import (
    InspectionCreate,
    InspectionRead,
    InspectionUpdate,
    InspectionWithMedia,
)
from app.schemas.media import MediaFileRead, MediaFileWithUrl
from app.services import storage

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post("", response_model=InspectionRead, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate, db: Session = Depends(get_db)
) -> Inspection:
    if db.get(Asset, payload.asset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"asset {payload.asset_id} not found",
        )
    inspection = Inspection(**payload.model_dump())
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("", response_model=list[InspectionWithMedia])
def list_inspections(
    db: Session = Depends(get_db),
    asset_id: uuid.UUID | None = None,
    status_filter: InspectionStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InspectionWithMedia]:
    # Left join + group by keeps this one query rather than one per inspection.
    stmt = (
        select(Inspection, func.count(MediaFile.id).label("media_count"))
        .outerjoin(MediaFile, MediaFile.inspection_id == Inspection.id)
        .group_by(Inspection.id)
        .order_by(Inspection.created_at.desc())
    )
    if asset_id is not None:
        stmt = stmt.where(Inspection.asset_id == asset_id)
    if status_filter is not None:
        stmt = stmt.where(Inspection.status == status_filter)

    rows = db.execute(stmt.limit(limit).offset(offset)).all()
    return [
        InspectionWithMedia(
            **InspectionRead.model_validate(inspection).model_dump(),
            media_count=count,
        )
        for inspection, count in rows
    ]


@router.get("/{inspection_id}", response_model=InspectionRead)
def get_inspection(
    inspection: Inspection = Depends(get_inspection_or_404),
) -> Inspection:
    return inspection


@router.patch("/{inspection_id}", response_model=InspectionRead)
def update_inspection(
    payload: InspectionUpdate,
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
) -> Inspection:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(inspection, field, value)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.delete("/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inspection(
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
) -> None:
    db.delete(inspection)
    db.commit()


@router.get("/{inspection_id}/media", response_model=list[MediaFileWithUrl])
def list_inspection_media(
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
) -> list[MediaFileWithUrl]:
    stmt = (
        select(MediaFile)
        .where(MediaFile.inspection_id == inspection.id)
        .order_by(MediaFile.created_at.asc())
    )
    return [
        MediaFileWithUrl(
            **MediaFileRead.model_validate(media).model_dump(),
            download_url=storage.presigned_url(media.storage_key),
        )
        for media in db.scalars(stmt)
    ]
