"""Test fixtures.

These are integration tests: they run against the real local Postgres and
MinIO from README setup step 6, not against mocks. That is deliberate for
Phase 1 — the whole point of the upload path is that bytes land in object
storage and a row lands in the database, and a mocked S3 client would not
prove either.

A dedicated `twinverse_test` database and `twinverse-test` bucket are created
and torn down, so running the suite never touches development data.

Environment variables are set before any `app` import, because the settings
object and SQLAlchemy engine are built at module import time.
"""

import os
import uuid

TEST_DB_NAME = "twinverse_test"
ADMIN_DSN = "postgresql+psycopg2://postgres:devpass@localhost:5432/twinverse"
TEST_DSN = f"postgresql+psycopg2://postgres:devpass@localhost:5432/{TEST_DB_NAME}"

os.environ["DATABASE_URL"] = TEST_DSN
os.environ["S3_BUCKET"] = "twinverse-test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import storage  # noqa: E402


def _recreate_test_database() -> None:
    admin = create_engine(ADMIN_DSN, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": TEST_DB_NAME},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _database():
    """Create the test database and apply the Alembic migration.

    Running the real migration rather than `Base.metadata.create_all` means the
    suite fails if the migration drifts from the models — which is the failure
    mode worth catching.
    """
    _recreate_test_database()

    from alembic import command
    from alembic.config import Config

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_root, "app/db/migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_DSN)
    command.upgrade(cfg, "head")

    yield

    engine.dispose()
    admin = create_engine(ADMIN_DSN, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": TEST_DB_NAME},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _bucket(_database):
    storage.ensure_bucket()
    yield
    client = storage.get_client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket):
        objects = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objects:
            client.delete_objects(
                Bucket=settings.s3_bucket, Delete={"Objects": objects}
            )
    client.delete_bucket(Bucket=settings.s3_bucket)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate between tests so each starts from a known state."""
    yield
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE assets, inspections, media_files, detections CASCADE")
        )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def asset(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/assets",
        json={
            "name": "Test Bridge",
            "asset_type": "bridge",
            "location": "Test Valley",
            "latitude": 51.5,
            "longitude": -0.12,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def inspection(client: TestClient, asset: dict) -> dict:
    resp = client.post(
        "/api/v1/inspections",
        json={"asset_id": asset["id"], "title": "Deck survey"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Test media generators ------------------------------------------------

def make_jpeg(width: int = 64, height: int = 48) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (120, 120, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def make_png(width: int = 32, height: int = 32) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (10, 200, 10)).save(buf, format="PNG")
    return buf.getvalue()


def make_mp4(frames: int = 10, width: int = 64, height: int = 48, fps: int = 10) -> bytes:
    """Write a tiny real mp4 so the video probe path is genuinely exercised."""
    import tempfile
    from pathlib import Path

    import cv2
    import numpy as np

    path = Path(tempfile.mkdtemp()) / f"{uuid.uuid4().hex}.mp4"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    for i in range(frames):
        frame = np.full((height, width, 3), (i * 20) % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data
