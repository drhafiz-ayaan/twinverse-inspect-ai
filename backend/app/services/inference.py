"""Defect detection.

Wraps a YOLO detector behind a small protocol so the ingest-to-database
pipeline can be exercised without loading real weights, and so the model can be
swapped (YOLOv11 → RT-DETR → a fine-tuned checkpoint) without touching callers.

Bounding boxes leave this module **normalized to 0..1** against the source
frame, matching how they are stored (README D-009).

Honest scope note: a stock COCO-pretrained YOLO detects people and cars, not
cracks. Until `ml/train.py` has produced a fine-tuned checkpoint and
`MODEL_WEIGHTS` points at it, this pipeline is plumbing that runs end to end but
does not yet detect real defects. See the README's Phase 2 section.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.db.models import DefectClass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RawDetection:
    """One detected box, before it becomes a database row.

    `bbox` is (x, y, width, height), normalized 0..1, origin top-left.
    """

    defect_class: DefectClass
    confidence: float
    bbox: tuple[float, float, float, float]
    frame_index: int | None = None

    @property
    def normalized_area(self) -> float:
        return self.bbox[2] * self.bbox[3]


# Maps model class names onto our four defect classes. Fine-tuned checkpoints
# from different datasets use different vocabularies, so aliases are collected
# here rather than assumed to match.
CLASS_ALIASES: dict[str, DefectClass] = {
    "crack": DefectClass.CRACK,
    "cracks": DefectClass.CRACK,
    "cracking": DefectClass.CRACK,
    "fissure": DefectClass.CRACK,
    "corrosion": DefectClass.CORROSION,
    "rust": DefectClass.CORROSION,
    "rusting": DefectClass.CORROSION,
    "surface_damage": DefectClass.SURFACE_DAMAGE,
    "surface damage": DefectClass.SURFACE_DAMAGE,
    "spalling": DefectClass.SURFACE_DAMAGE,
    "scaling": DefectClass.SURFACE_DAMAGE,
    "erosion": DefectClass.SURFACE_DAMAGE,
    "pothole": DefectClass.SURFACE_DAMAGE,
    "missing_component": DefectClass.MISSING_COMPONENT,
    "missing component": DefectClass.MISSING_COMPONENT,
    "missing_bolt": DefectClass.MISSING_COMPONENT,
    "missing": DefectClass.MISSING_COMPONENT,
    # Exposed reinforcement: the concrete cover is gone. Filed under
    # MISSING_COMPONENT rather than SURFACE_DAMAGE because it is the missing
    # cover that matters — exposed rebar corrodes and the section loses
    # capacity, so it warrants the 1.0 class weight rather than 0.6.
    "exposed_bar": DefectClass.MISSING_COMPONENT,
    "exposed bar": DefectClass.MISSING_COMPONENT,
    "exposed_rebar": DefectClass.MISSING_COMPONENT,
    "exposed rebar": DefectClass.MISSING_COMPONENT,
    "rebar": DefectClass.MISSING_COMPONENT,
}

# Deliberately absent: "stain".
#
# Staining is a *symptom* — usually water ingress or leaching — not structural
# damage. The concrete-bridge-defect dataset labels it, and the model is trained
# on it (knowing what a stain looks like helps it avoid calling one a crack),
# but stain detections are discarded here rather than scored. Counting stains as
# defects would inflate severity totals with something no structural engineer
# would call a defect, which is exactly the overclaiming D-004 exists to avoid.


def map_class_name(name: str) -> DefectClass | None:
    """Resolve a model's label to a defect class, or None to discard it.

    Returning None rather than defaulting to a class is deliberate: silently
    filing a detected "person" under `crack` would corrupt every downstream
    severity number.
    """
    return CLASS_ALIASES.get(name.strip().lower().replace("-", "_"))


@dataclass(slots=True)
class AnalysisResult:
    detections: list[RawDetection]
    frames_analyzed: int


class Detector(Protocol):
    """The seam that lets tests run the pipeline without real weights."""

    @property
    def weights(self) -> str: ...

    def analyze_image(self, path: Path) -> AnalysisResult: ...

    def analyze_video(self, path: Path) -> AnalysisResult: ...


class YoloDetector:
    """Ultralytics YOLO backend.

    The model is loaded lazily and held for the process lifetime — loading
    weights costs far more than running a single image, so paying it per request
    would dominate latency.
    """

    def __init__(
        self,
        weights: str | None = None,
        confidence: float | None = None,
        device: str | None = None,
    ) -> None:
        self._weights = weights or settings.model_weights
        self._confidence = (
            confidence if confidence is not None else settings.confidence_threshold
        )
        self._device = device if device is not None else settings.inference_device
        self._model = None

    @property
    def weights(self) -> str:
        return self._weights

    def _load(self):
        if self._model is None:
            from ultralytics import YOLO

            logger.info("loading detector weights: %s", self._weights)
            self._model = YOLO(self._weights)
        return self._model

    def _predict(self, source, frame_index: int | None = None) -> list[RawDetection]:
        model = self._load()
        kwargs: dict[str, object] = {"conf": self._confidence, "verbose": False}
        if self._device:
            kwargs["device"] = self._device

        out: list[RawDetection] = []
        for result in model.predict(source, **kwargs):
            names = result.names
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            # xywhn: centre-x, centre-y, width, height, all normalized.
            for xywhn, conf, cls_id in zip(
                boxes.xywhn.tolist(), boxes.conf.tolist(), boxes.cls.tolist()
            ):
                defect = map_class_name(names[int(cls_id)])
                if defect is None:
                    continue
                cx, cy, w, h = xywhn
                out.append(
                    RawDetection(
                        defect_class=defect,
                        confidence=float(conf),
                        # Convert centre-origin to top-left origin and clamp, so
                        # a box touching the frame edge cannot go negative.
                        bbox=(
                            max(0.0, cx - w / 2),
                            max(0.0, cy - h / 2),
                            min(1.0, w),
                            min(1.0, h),
                        ),
                        frame_index=frame_index,
                    )
                )
        return out

    def analyze_image(self, path: Path) -> AnalysisResult:
        return AnalysisResult(self._predict(str(path)), frames_analyzed=1)

    def analyze_video(self, path: Path) -> AnalysisResult:
        """Sample frames rather than decoding every one.

        Adjacent video frames show the same defect from almost the same angle,
        so processing all of them multiplies runtime and fills the table with
        near-duplicate rows for no extra information.
        """
        import cv2

        stride = max(1, settings.video_frame_stride)
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            logger.warning("could not open video for inference: %s", path)
            return AnalysisResult([], frames_analyzed=0)

        detections: list[RawDetection] = []
        analyzed = 0
        index = 0
        try:
            while analyzed < settings.video_max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                if index % stride == 0:
                    detections.extend(self._predict(frame, frame_index=index))
                    analyzed += 1
                index += 1
        finally:
            cap.release()

        return AnalysisResult(detections, frames_analyzed=analyzed)


@lru_cache
def get_detector() -> Detector:
    """Process-wide detector. Cached so weights load once."""
    return YoloDetector()


_override: Detector | None = None


def set_detector(detector: Detector | None) -> None:
    """Install a detector, or pass None to restore the default.

    Used by tests to exercise the full persistence path against a predictable
    stub instead of downloading weights.
    """
    global _override
    _override = detector


def active_detector() -> Detector:
    return _override if _override is not None else get_detector()


def analyze(path: Path, media_type) -> AnalysisResult:
    from app.db.models import MediaType

    detector = active_detector()
    if media_type is MediaType.VIDEO:
        return detector.analyze_video(path)
    return detector.analyze_image(path)
