"""Authentication and user management."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_admin
from app.core import security
from app.core.config import settings
from app.db.models import User, UserRole
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange credentials for an access token.

    A wrong password and an unknown address return the same 401, and the
    password is verified even when no user matched, so response timing does
    not reveal which addresses are registered.
    """
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    if user is None:
        # Compare against a throwaway hash to keep the timing comparable.
        security.verify_password(
            payload.password, security.hash_password("no-such-user")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
        )

    if not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="account is disabled"
        )

    return TokenResponse(
        access_token=security.create_access_token(user.id, user.role.value),
        expires_in=settings.access_token_expire_minutes * 60,
        role=user.role,
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.post(
    "/users", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    try:
        hashed = security.hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    user = User(
        email=payload.email.lower(),
        hashed_password=hashed,
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a user with that email already exists",
        )
    db.refresh(user)
    logger.info("created user %s with role %s", user.email, user.role.value)
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at)))


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )

    changes = payload.model_dump(exclude_unset=True)

    # Guard against an administrator locking everyone out of user management
    # by demoting or disabling the last remaining admin — including themselves.
    demoting = changes.get("role") not in (None, UserRole.ADMIN) and "role" in changes
    disabling = changes.get("is_active") is False
    if user.role is UserRole.ADMIN and (demoting or disabling):
        remaining = db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
                User.id != user.id,
            )
        )
        if not remaining:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="cannot demote or disable the last active admin",
            )

    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    logger.info("user %s updated by %s", user.email, actor.email)
    return user
