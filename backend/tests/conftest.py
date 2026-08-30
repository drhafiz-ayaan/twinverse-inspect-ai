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
# A real (throwaway) signing key, so the suite exercises the same startup path
# as production rather than the DEBUG escape hatch.
os.environ["SECRET_KEY"] = "test-only-key-nGf3xQ2pLm8vTz9RwK4bYc7HdJs1AeUo"
os.environ.pop("BOOTSTRAP_ADMIN_EMAIL", None)
os.environ.pop("BOOTSTRAP_ADMIN_PASSWORD", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core import security  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import User, UserRole  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import storage  # noqa: E402

# Fixed credentials for the suite's three roles.
PASSWORD = "test-password-123"
ROLE_EMAILS = {
    UserRole.VIEWER: "viewer@example.com",
    UserRole.INSPECTOR: "inspector@example.com",
    UserRole.ADMIN: "admin@example.com",
}


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


@pytest.fixture(scope="session", autouse=True)
def _users(_database):
    """One account per role, created once for the whole suite.

    Deliberately outside the per-test truncation: re-hashing bcrypt passwords
    for every test would dominate the runtime for no benefit.
    """
    db = SessionLocal()
    try:
        for role, email in ROLE_EMAILS.items():
            db.add(
                User(
                    email=email,
                    hashed_password=security.hash_password(PASSWORD),
                    full_name=role.value.title(),
                    role=role,
                )
            )
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate between tests so each starts from a known state.

    `users` is excluded — the role accounts are session-scoped.
    """
    yield
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE assets, inspections, media_files, detections CASCADE")
        )
        # Drop any users a test created, keeping the three role accounts.
        conn.execute(
            text("DELETE FROM users WHERE email NOT IN :keep").bindparams(
                keep=tuple(ROLE_EMAILS.values())
            )
        )


def _token(role: UserRole) -> str:
    resp = TestClient(app).post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[role], "password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _client_for(role: UserRole) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {_token(role)}"})
    return c


@pytest.fixture
def client(_users) -> TestClient:
    """Default client: INSPECTOR, the role that does the day-to-day work."""
    return _client_for(UserRole.INSPECTOR)


@pytest.fixture
def viewer_client(_users) -> TestClient:
    return _client_for(UserRole.VIEWER)


@pytest.fixture
def admin_client(_users) -> TestClient:
    return _client_for(UserRole.ADMIN)


@pytest.fixture
def anon_client() -> TestClient:
    """No credentials at all."""
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
