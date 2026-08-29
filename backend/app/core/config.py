"""Application configuration.

Values are read from environment variables, falling back to a local `.env`
file. Defaults match the local development services documented in the README
(step 6), so a fresh checkout runs without a `.env` present.

Never commit real credentials: `.env` is gitignored, `.env.example` is not.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "TwinVerse Inspect AI"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # --- Database ---
    database_url: str = "postgresql+psycopg2://postgres:devpass@localhost:5432/twinverse"

    # --- Object storage (MinIO / any S3-compatible endpoint) ---
    # Swapping to Alibaba Cloud OSS or AWS S3 is a change to these values only.
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "twinverse-inspections"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    # --- Upload limits ---
    max_image_bytes: int = Field(default=25 * 1024 * 1024)   # 25 MB
    max_video_bytes: int = Field(default=500 * 1024 * 1024)  # 500 MB

    allowed_image_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/tiff",
        "image/bmp",
    )
    allowed_video_types: tuple[str, ...] = (
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska",
        "video/webm",
    )

    # Presigned download links handed to the dashboard.
    presign_expiry_seconds: int = 3600

    @property
    def allowed_content_types(self) -> tuple[str, ...]:
        return self.allowed_image_types + self.allowed_video_types


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the `.env` file is parsed once per process."""
    return Settings()


settings = get_settings()
