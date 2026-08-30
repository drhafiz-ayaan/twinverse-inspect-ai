"""Severity scoring.

    severity_score = normalized_area x confidence x class_weight

Deliberately simple and deliberately *visible*: the formula is exposed through
the API so the dashboard can show it rather than presenting a number to be
taken on trust. Explainability is a stated judging advantage, and a score you
cannot re-derive is not explainable.

The inputs are stored alongside the result on every detection row, so any
score in the database can be recomputed by hand from its own record.

Stated limitation, per README D-004: this is a *relative* ranking. It does not
output engineering units — crack width in millimetres needs camera calibration
or a scale reference in frame. Presenting it honestly is the point.
"""

from __future__ import annotations

from app.core.config import settings
from app.db.models import DefectClass, Detection, SeverityBand

# Per README. A crack and a missing component are structural; surface damage
# is cosmetic until it is not.
CLASS_WEIGHTS: dict[DefectClass, float] = {
    DefectClass.CRACK: 1.0,
    DefectClass.CORROSION: 0.9,
    DefectClass.SURFACE_DAMAGE: 0.6,
    DefectClass.MISSING_COMPONENT: 1.0,
}


def class_weight(defect_class: DefectClass) -> float:
    return CLASS_WEIGHTS.get(defect_class, 1.0)


def score(normalized_area: float, confidence: float,
          defect_class: DefectClass) -> float:
    """The formula. Three multiplications, nothing hidden."""
    return normalized_area * confidence * class_weight(defect_class)


def band(value: float) -> SeverityBand:
    """Map a score onto a band using the configured cut points."""
    if value < settings.severity_band_medium:
        return SeverityBand.LOW
    if value < settings.severity_band_high:
        return SeverityBand.MEDIUM
    if value < settings.severity_band_critical:
        return SeverityBand.HIGH
    return SeverityBand.CRITICAL


def apply(detection: Detection) -> Detection:
    """Populate the severity fields on a detection row, in place.

    `normalized_area` is written by the detection pipeline (it is geometry, and
    free); everything else is computed here. Called at detection time and by
    the rescore endpoint, so a band-threshold change can be applied to existing
    rows without re-running inference.
    """
    area = detection.normalized_area
    if area is None:
        area = detection.bbox_width * detection.bbox_height
        detection.normalized_area = area

    weight = class_weight(detection.defect_class)
    value = score(area, detection.confidence, detection.defect_class)

    detection.class_weight = weight
    detection.severity_score = value
    detection.severity_band = band(value)
    return detection


def describe() -> dict[str, object]:
    """The scoring model as data, for the UI to render.

    Returned by GET /api/v1/severity/model so the dashboard shows the actual
    formula and thresholds in force rather than a hardcoded copy that can drift
    from what the server computes.
    """
    return {
        "formula": "severity_score = normalized_area x confidence x class_weight",
        "class_weights": {c.value: w for c, w in CLASS_WEIGHTS.items()},
        "bands": {
            "low": [0.0, settings.severity_band_medium],
            "medium": [settings.severity_band_medium, settings.severity_band_high],
            "high": [settings.severity_band_high, settings.severity_band_critical],
            "critical": [settings.severity_band_critical, 1.0],
        },
        "limitation": (
            "Relative ranking only. Does not output engineering units: crack "
            "width in millimetres requires camera calibration or a scale "
            "reference in frame."
        ),
    }
