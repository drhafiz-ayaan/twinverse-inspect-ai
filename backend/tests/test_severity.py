"""Severity scoring."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models import DefectClass, Detection, SeverityBand
from app.services import inference, severity
from app.services.inference import RawDetection
from tests.conftest import make_jpeg
from tests.test_detections import StubDetector


# --- the formula ---------------------------------------------------------

def test_formula_is_three_multiplications() -> None:
    """The score must be re-derivable by hand from its own inputs.

    D-004 commits to showing the formula on screen; that is only honest if the
    displayed number equals area x confidence x weight exactly.
    """
    assert severity.score(0.02, 0.5, DefectClass.CRACK) == pytest.approx(0.01)
    assert severity.score(0.02, 0.5, DefectClass.SURFACE_DAMAGE) == pytest.approx(
        0.02 * 0.5 * 0.6
    )


@pytest.mark.parametrize(
    "defect_class,weight",
    [
        (DefectClass.CRACK, 1.0),
        (DefectClass.CORROSION, 0.9),
        (DefectClass.SURFACE_DAMAGE, 0.6),
        (DefectClass.MISSING_COMPONENT, 1.0),
    ],
)
def test_class_weights_match_the_documented_table(defect_class, weight) -> None:
    assert severity.class_weight(defect_class) == weight


def test_zero_area_scores_zero() -> None:
    assert severity.score(0.0, 0.99, DefectClass.CRACK) == 0.0


def test_score_is_monotonic_in_each_input() -> None:
    base = severity.score(0.02, 0.5, DefectClass.CRACK)
    assert severity.score(0.03, 0.5, DefectClass.CRACK) > base
    assert severity.score(0.02, 0.7, DefectClass.CRACK) > base
    assert severity.score(0.02, 0.5, DefectClass.SURFACE_DAMAGE) < base


# --- bands ---------------------------------------------------------------

def test_bands_partition_the_range() -> None:
    m, h, c = (
        settings.severity_band_medium,
        settings.severity_band_high,
        settings.severity_band_critical,
    )
    assert severity.band(0.0) is SeverityBand.LOW
    assert severity.band(m - 1e-9) is SeverityBand.LOW
    assert severity.band(m) is SeverityBand.MEDIUM
    assert severity.band(h - 1e-9) is SeverityBand.MEDIUM
    assert severity.band(h) is SeverityBand.HIGH
    assert severity.band(c - 1e-9) is SeverityBand.HIGH
    assert severity.band(c) is SeverityBand.CRITICAL
    assert severity.band(1.0) is SeverityBand.CRITICAL


def test_bands_are_calibrated_not_the_proposal_defaults() -> None:
    """Guards D-018 against a well-meaning revert.

    The proposal's 0.25/0.50/0.75 put 100% of 308 measured detections in LOW,
    because the score is a box's share of the frame times a confidence below
    one. The guard is that the thresholds are *measured*, not round.

    It deliberately does not pin an absolute ceiling. The original bands sat
    near 0.009 because that model drew tight boxes; a model trained on
    polygon-derived annotations draws much larger ones and calibrates near
    0.058 — six times higher and equally correct. An earlier version of this
    test asserted `medium < 0.05` and would have failed a legitimate
    recalibration, which is the wrong thing for a guard to do.
    """
    m = settings.severity_band_medium
    h = settings.severity_band_high
    c = settings.severity_band_critical

    assert 0 < m < h < c, "bands must be ordered and non-zero"
    # The proposal's exact values, and anything in their neighbourhood: a
    # crack's box is a few percent of a frame, so a MEDIUM cut at a quarter of
    # the maximum possible score puts everything in LOW whatever the model.
    assert (m, h, c) != (0.25, 0.50, 0.75)
    assert m < 0.25, "MEDIUM this high makes the band a constant"

    # Whatever the calibration, the bands must actually partition: a score at
    # each cut point lands in the band above it.
    assert severity.band(m) is SeverityBand.MEDIUM
    assert severity.band(c) is SeverityBand.CRITICAL


# --- application to rows -------------------------------------------------

def test_apply_populates_all_severity_fields() -> None:
    d = Detection(
        defect_class=DefectClass.CRACK,
        confidence=0.6,
        bbox_x=0.1, bbox_y=0.1, bbox_width=0.2, bbox_height=0.1,
        normalized_area=0.02,
    )
    severity.apply(d)
    assert d.class_weight == 1.0
    # The score is the invariant — three multiplications, no configuration.
    assert d.severity_score == pytest.approx(0.012)
    # The band is not: it depends on thresholds that are recalibrated whenever
    # the model changes. Asserting a literal band here pins the test to one
    # checkpoint's score distribution, so assert that apply() routed the score
    # through the configured cut points rather than what those points are.
    assert d.severity_band is severity.band(d.severity_score)
    assert d.severity_band is not None


def test_apply_derives_area_when_missing() -> None:
    """A row written without normalized_area must still score correctly."""
    d = Detection(
        defect_class=DefectClass.CRACK,
        confidence=0.5,
        bbox_x=0.0, bbox_y=0.0, bbox_width=0.2, bbox_height=0.1,
        normalized_area=None,
    )
    severity.apply(d)
    assert d.normalized_area == pytest.approx(0.02)
    assert d.severity_score == pytest.approx(0.01)


# --- through the API -----------------------------------------------------

@pytest.fixture
def scored(client: TestClient, inspection: dict) -> dict:
    detector = StubDetector(
        detections=[
            RawDetection(DefectClass.CRACK, 0.60, (0.1, 0.1, 0.20, 0.10)),
            RawDetection(DefectClass.CRACK, 0.40, (0.5, 0.5, 0.05, 0.05)),
        ]
    )
    inference.set_detector(detector)
    try:
        media = client.post(
            f"/api/v1/inspections/{inspection['id']}/uploads",
            files=[("files", ("a.jpg", make_jpeg(), "image/jpeg"))],
        ).json()["results"][0]["media_file"]
        client.post(f"/api/v1/media/{media['id']}/detect")
        yield {"inspection": inspection, "media": media}
    finally:
        inference.set_detector(None)


def test_detections_are_scored_when_written(client: TestClient, scored: dict) -> None:
    rows = client.get(
        f"/api/v1/media/{scored['media']['id']}/detections"
    ).json()
    assert len(rows) == 2
    for row in rows:
        assert row["severity_score"] is not None
        assert row["severity_band"] is not None
        assert row["class_weight"] == 1.0
        # Re-derive it exactly, the way the UI claims a reader can.
        assert row["severity_score"] == pytest.approx(
            row["normalized_area"] * row["confidence"] * row["class_weight"]
        )


def test_summary_reports_severity_distribution(
    client: TestClient, scored: dict
) -> None:
    s = client.get(
        f"/api/v1/inspections/{scored['inspection']['id']}/detections/summary"
    ).json()
    assert sum(b["count"] for b in s["by_severity"]) == 2
    assert s["max_severity_score"] == pytest.approx(0.012)
    assert s["mean_severity_score"] is not None


def test_severity_model_endpoint_exposes_the_formula(client: TestClient) -> None:
    """The dashboard renders this rather than a hardcoded copy."""
    body = client.get("/api/v1/severity/model").json()
    assert "normalized_area" in body["formula"]
    assert body["class_weights"]["crack"] == 1.0
    assert body["class_weights"]["surface_damage"] == 0.6
    assert set(body["bands"]) == {"low", "medium", "high", "critical"}
    assert "millimetre" in body["limitation"]


def test_rescore_applies_new_thresholds_without_reinference(
    client: TestClient, scored: dict, monkeypatch
) -> None:
    """Band thresholds are config, so changing them must not need the GPU."""
    before = client.get(
        f"/api/v1/inspections/{scored['inspection']['id']}/detections"
    ).json()
    assert any(r["severity_band"] != "critical" for r in before)

    monkeypatch.setattr(settings, "severity_band_medium", 0.0)
    monkeypatch.setattr(settings, "severity_band_high", 0.0)
    monkeypatch.setattr(settings, "severity_band_critical", 0.0)

    resp = client.post(f"/api/v1/inspections/{scored['inspection']['id']}/rescore")
    assert resp.status_code == 200
    assert resp.json()["rescored"] == 2

    after = client.get(
        f"/api/v1/inspections/{scored['inspection']['id']}/detections"
    ).json()
    assert all(r["severity_band"] == "critical" for r in after)
