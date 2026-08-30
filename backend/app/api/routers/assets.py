"""Asset CRUD."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_asset_or_404, require_admin, require_inspector
from app.db.models import Asset, AssetType
from app.db.session import get_db
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_inspector),
) -> Asset:
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    asset_type: AssetType | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.created_at.desc())
    if asset_type is not None:
        stmt = stmt.where(Asset.asset_type == asset_type)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset: Asset = Depends(get_asset_or_404)) -> Asset:
    return asset


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    payload: AssetUpdate,
    asset: Asset = Depends(get_asset_or_404),
    db: Session = Depends(get_db),
    _: object = Depends(require_inspector),
) -> Asset:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset: Asset = Depends(get_asset_or_404),
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
) -> None:
    """Deletes the asset and, by cascade, its inspections and media rows.

    Note: this does not remove the underlying objects from the bucket. Object
    reclamation is deliberately left to a separate sweep so a mistaken delete
    stays recoverable.
    """
    db.delete(asset)
    db.commit()
