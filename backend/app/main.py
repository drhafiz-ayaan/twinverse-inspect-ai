"""FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    assets,
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
    # Creating the bucket at boot means the first upload of a fresh environment
    # does not fail on a missing bucket. Failure here is logged, not fatal: the
    # readiness probe reports it, and the app can still serve reads.
    try:
        storage.ensure_bucket()
        logger.info("object storage ready: bucket %s", settings.s3_bucket)
    except storage.StorageError:
        logger.exception("object storage unavailable at startup")
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

app.include_router(health.router)
app.include_router(assets.router, prefix=settings.api_v1_prefix)
app.include_router(inspections.router, prefix=settings.api_v1_prefix)
app.include_router(uploads.router, prefix=settings.api_v1_prefix)
app.include_router(detections.router, prefix=settings.api_v1_prefix)
app.include_router(reports.router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
