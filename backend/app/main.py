"""FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import require_viewer
from app.api.routers import (
    assets,
    auth,
    detections,
    health,
    inspections,
    reports,
    uploads,
)
from app.core.config import settings
from app.services import storage

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key_is_default:
        message = (
            "SECRET_KEY is the built-in development default. Tokens signed "
            "with it are forgeable by anyone who has read this source."
        )
        if settings.debug:
            logger.warning("%s Acceptable only because DEBUG is on.", message)
        else:
            # Fail closed. A deployment running on a published signing key is
            # worse than one that refuses to start.
            raise RuntimeError(
                message + " Set SECRET_KEY, or run with DEBUG=true for local "
                "development. Generate one with: python -c \"import secrets; "
                "print(secrets.token_urlsafe(48))\""
            )

    # Creating the bucket at boot means the first upload of a fresh environment
    # does not fail on a missing bucket. Failure here is logged, not fatal: the
    # readiness probe reports it, and the app can still serve reads.
    try:
        storage.ensure_bucket()
        logger.info("object storage ready: bucket %s", settings.s3_bucket)
    except Exception:
        # Never fatal. The readiness probe reports it and the app still serves
        # reads; an orchestrator restarting on a slow dependency is worse than
        # a degraded instance that recovers on its own.
        logger.exception("object storage unavailable at startup")

    _bootstrap_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered infrastructure inspection. Phase 1: asset, inspection and "
        "media ingest."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# The Next.js dashboard is a separate origin in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health is public so an orchestrator can probe it without credentials.
app.include_router(health.router)

# Login must be reachable unauthenticated; the router guards its own
# admin-only endpoints.
app.include_router(auth.router, prefix=settings.api_v1_prefix)

# Everything else needs at least a VIEWER. Applying the baseline here rather
# than per-endpoint means a newly added route is protected by default —
# forgetting a decorator fails closed instead of leaking data.
_authenticated = [Depends(require_viewer)]
for module in (assets, inspections, uploads, detections, reports):
    app.include_router(
        module.router, prefix=settings.api_v1_prefix, dependencies=_authenticated
    )


def _bootstrap_admin() -> None:
    """Create the first administrator when the users table is empty.

    Without this a fresh deployment has no way in: every user-creation route
    requires an existing admin. Runs only when there are zero users, so it
    cannot silently re-add a deliberately deleted account.
    """
    if not (settings.bootstrap_admin_email and settings.bootstrap_admin_password):
        return

    # Validate with the same rule the login schema uses. The ORM accepts any
    # string, so without this a bootstrap address like admin@example.local
    # creates an account that /auth/login then rejects as invalid — an admin
    # you can never sign in as, and no obvious reason why.
    from pydantic import ValidationError

    from app.schemas.auth import LoginRequest

    try:
        LoginRequest(
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
        )
    except ValidationError as exc:
        logger.error(
            "BOOTSTRAP_ADMIN_EMAIL %r is not an address the login endpoint "
            "will accept, so no admin was created: %s",
            settings.bootstrap_admin_email,
            exc.errors()[0].get("msg", ""),
        )
        return

    from sqlalchemy import func, select

    from app.core import security
    from app.db.models import User, UserRole
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        if db.scalar(select(func.count(User.id))):
            return
        db.add(
            User(
                email=settings.bootstrap_admin_email.lower(),
                hashed_password=security.hash_password(
                    settings.bootstrap_admin_password
                ),
                full_name="Bootstrap Admin",
                role=UserRole.ADMIN,
            )
        )
        db.commit()
        logger.warning(
            "created bootstrap admin %s - change this password immediately",
            settings.bootstrap_admin_email,
        )
    except Exception:
        db.rollback()
        logger.exception("bootstrap admin creation failed")
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
