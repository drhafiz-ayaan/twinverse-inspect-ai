"""Shared API dependencies."""

import uuid

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.db.models import ROLE_RANK, Asset, Inspection, MediaFile, User, UserRole
from app.db.session import get_db

# auto_error=False so a missing header produces our 401 with a WWW-Authenticate
# challenge rather than Starlette's bare 403.
_bearer = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to an active user.

    Every failure returns the same 401: an invalid signature, an expired
    token and a deleted account are indistinguishable to the caller, so this
    cannot be used to probe which accounts exist.
    """
    if credentials is None or not credentials.credentials:
        raise _UNAUTHENTICATED

    claims = security.decode_access_token(credentials.credentials)
    if claims is None:
        raise _UNAUTHENTICATED

    try:
        user_id = uuid.UUID(str(claims.get("sub")))
    except (ValueError, TypeError):
        raise _UNAUTHENTICATED

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED

    # The role is re-read from the database rather than trusted from the token,
    # so a demotion takes effect immediately instead of when the token expires.
    return user


def require_role(minimum: UserRole):
    """Dependency factory enforcing a minimum role.

    Roles are ranked, so INSPECTOR satisfies a VIEWER requirement without a
    hand-maintained membership table.
    """

    def guard(user: User = Depends(current_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires {minimum.value} role or higher",
            )
        return user

    return guard


require_viewer = require_role(UserRole.VIEWER)
require_inspector = require_role(UserRole.INSPECTOR)
require_admin = require_role(UserRole.ADMIN)


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
