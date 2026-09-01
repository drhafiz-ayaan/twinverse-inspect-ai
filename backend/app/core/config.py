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
    # Endpoint used only to sign download links for the browser. Under Compose
    # the API reaches MinIO at http://minio:9000, a hostname that exists only on
    # the Docker network — presigning with it produces URLs the browser cannot
    # resolve, and every image in the dashboard fails to load. Set this to the
    # address a browser can reach. Unset, it falls back to s3_endpoint_url,
    # which is correct when running outside containers.
    s3_public_endpoint_url: str | None = None
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
    #
    # 0.10 is low on purpose. It was chosen by simulating inspection campaigns
    # (ml/simulate_inspection.py) rather than by maximising detection rate minus
    # false-alarm rate — that metric treats a missed crack and a false alarm as
    # equally bad, and in structural inspection they are not. A missed crack is
    # found at the next survey or when something fails; a false alarm costs an
    # engineer half a minute. This threshold is the lowest worst-case miss rate
    # across every dataset measured, at the cost of a larger review pile.
    confidence_threshold: float = 0.10

    # Video is sampled rather than processed frame by frame: a 60 s clip at
    # 30 fps is 1800 frames, and adjacent frames show the same defect. Sampling
    # every Nth frame keeps runtime and duplicate rows down.
    video_frame_stride: int = 15
    video_max_frames: int = 300

    # --- Severity bands (Phase 3) ---
    # Cut points for LOW/MEDIUM/HIGH/CRITICAL against
    #   severity = normalized_area x confidence x class_weight
    #
    # The proposal's original 0.25/0.50/0.75 assume the score spans 0..1. It
    # does not for thin defects: a crack's bounding box covers a few percent of
    # the frame, so every detection was filed as LOW and the band carried no
    # information at all (README D-018).
    #
    # These cut points are the p52/p76/p94 of measured output, giving roughly
    # 53/24/17/6 percent across LOW/MEDIUM/HIGH/CRITICAL. Two things determine
    # them, and both must be held in mind together:
    #
    #   The model. crack-nitw-bg calibrated near 0.009/0.011/0.014; the current
    #   crack-hardneg draws much larger boxes, having been trained on
    #   polygon-derived annotations.
    #
    #   The confidence threshold. These values are calibrated at conf 0.10,
    #   the deployed operating point. The same model at conf 0.30 calibrates
    #   ten times higher, because raising the threshold discards precisely the
    #   small low-confidence detections that populate the bottom of the
    #   distribution. **Never change one without recalibrating the other.**
    #
    # Regenerate with ml/calibrate_bands.py, then POST
    # /inspections/{id}/rescore to re-apply them without re-running inference.
    # Dataset-relative by construction, consistent with D-004: this ranks
    # defects against each other, it does not measure them.
    severity_band_medium: float = 0.0060
    severity_band_high: float = 0.0163
    severity_band_critical: float = 0.1653

    # --- Auth (Phase 6) ---
    # Signs JWTs. The default is a development placeholder and the app refuses
    # to start with it when debug is off — see app/main.py. Generate one with:
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: str = "dev-only-insecure-key-change-me"
    access_token_expire_minutes: int = 60 * 12

    # Bootstrap administrator, created at startup when no users exist. Leave
    # the password unset in any deployed environment and create the first user
    # deliberately instead.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    @property
    def secret_key_is_default(self) -> bool:
        return self.secret_key == "dev-only-insecure-key-change-me"

    @property
    def allowed_content_types(self) -> tuple[str, ...]:
        return self.allowed_image_types + self.allowed_video_types


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the `.env` file is parsed once per process."""
    return Settings()


settings = get_settings()
