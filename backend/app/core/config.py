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

    # --- Inference (Phase 2) ---
    # Path to YOLO weights. A bare name like "yolo11n.pt" is resolved by
    # Ultralytics against its own cache and downloaded on first use; a filesystem
    # path points at a fine-tuned checkpoint from ml/train.py.
    model_weights: str = "yolo11n.pt"

    # "cuda:0", "cpu", or None to let Ultralytics choose.
    inference_device: str | None = None

    # Boxes below this confidence are discarded before they reach the database.
    confidence_threshold: float = 0.25

    # Video is sampled rather than processed frame by frame: a 60 s clip at
    # 30 fps is 1800 frames, and adjacent frames show the same defect. Sampling
    # every Nth frame keeps runtime and duplicate rows down.
    video_frame_stride: int = 15
    video_max_frames: int = 300

    # --- Severity bands (Phase 3) ---
    # Cut points for LOW/MEDIUM/HIGH/CRITICAL against
    #   severity = normalized_area x confidence x class_weight
    #
    # Calibrated against 308 real detections (see README D-018). The proposal's
    # original 0.25/0.50/0.75 assume the score spans 0..1; it does not for thin
    # defects. A crack's bounding box covers 2-4% of the frame, so scores land
    # near 0.009 and the maximum observed was 0.021 — every detection filed as
    # LOW, making the band useless.
    #
    # These cut points sit near the p52/p76/p94 of measured output, giving
    # roughly 53/24/17/6 percent across LOW/MEDIUM/HIGH/CRITICAL.
    #
    # They are dataset-relative by construction, consistent with D-004: this
    # ranks defects against each other, it does not measure them. Recalibrate
    # after any model change, then POST /inspections/{id}/rescore.
    severity_band_medium: float = 0.009
    severity_band_high: float = 0.011
    severity_band_critical: float = 0.014

    @property
    def allowed_content_types(self) -> tuple[str, ...]:
        return self.allowed_image_types + self.allowed_video_types


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the `.env` file is parsed once per process."""
    return Settings()


settings = get_settings()
