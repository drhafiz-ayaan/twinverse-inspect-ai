"""Detection pipeline.

These exercise storage → inference → database against a **stub detector**. The
point is to prove the plumbing and persistence, which is what can break without
anyone noticing; whether YOLO finds real cracks is a question about weights and
training data, not about this code, and it is answered by ml/train.py metrics.

Using a stub also keeps the suite from depending on a model download.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.models import DefectClass
from app.services import inference
from app.services.inference import AnalysisResult, RawDetection, map_class_name
from tests.conftest import make_jpeg, make_mp4


class StubDetector:
    """Returns a fixed set of boxes, recording what it was asked to analyze."""

    def __init__(self, detections=None, frames=1, weights="stub.pt"):
        self._detections = detections if detections is not None else [
            RawDetection(DefectClass.CRACK, 0.91, (0.10, 0.20, 0.30, 0.40)),
            RawDetection(DefectClass.CORROSION, 0.42, (0.50, 0.50, 0.20, 0.10)),
        ]
        self._frames = frames
        self._weights = weights
        self.calls: list[tuple[str, Path]] = []

    @property
    def weights(self) -> str:
        return self._weights

    def analyze_image(self, path: Path) -> AnalysisResult:
        self.calls.append(("image", path))
        return AnalysisResult(list(self._detections), frames_analyzed=1)

    def analyze_video(self, path: Path) -> AnalysisResult:
        self.calls.append(("video", path))
        return AnalysisResult(list(self._detections), frames_analyzed=self._frames)


@pytest.fixture
def stub() -> StubDetector:
    detector = StubDetector()
    inference.set_detector(detector)
    yield detector
    inference.set_detector(None)


@pytest.fixture
def uploaded_image(client: TestClient, inspection: dict) -> dict:
    resp = client.post(
        f"/api/v1/inspections/{inspection['id']}/uploads",
        files=[("files", ("pier.jpg", make_jpeg(200, 150), "image/jpeg"))],
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["results"][0]["media_file"]


# --- class mapping --------------------------------------------------------

@pytest.mark.parametrize(
    "name,expected",
    [
        ("crack", DefectClass.CRACK),
        ("Cracks", DefectClass.CRACK),
        ("rust", DefectClass.CORROSION),
        ("spalling", DefectClass.SURFACE_DAMAGE),
        ("missing-bolt", DefectClass.MISSING_COMPONENT),
        ("  CRACK  ", DefectClass.CRACK),
    ],
)
def test_known_class_names_map(name, expected) -> None:
    assert map_class_name(name) is expected


@pytest.mark.parametrize("name", ["person", "car", "traffic light", ""])
def test_unknown_class_names_are_discarded(name) -> None:
    """Never guess. A 'person' filed as a crack corrupts every severity score."""
    assert map_class_name(name) is None


@pytest.mark.parametrize(
    "name,expected",
    [
        ("crack", DefectClass.CRACK),
        ("spalling", DefectClass.SURFACE_DAMAGE),
        ("exposed-bar", DefectClass.MISSING_COMPONENT),
    ],
)
def test_bridge_dataset_classes_map(name, expected) -> None:
    """The three scored classes of ycc-otptp/concrete-bridge-defect v6.

    Exposed rebar is MISSING_COMPONENT, not SURFACE_DAMAGE: it is the absent
    concrete cover that matters, and it carries the 1.0 class weight rather
    than 0.6 accordingly.
    """
    assert map_class_name(name) is expected


def test_stain_is_deliberately_not_a_defect() -> None:
    """Staining is a symptom of water ingress, not structural damage.

    The model is trained on the class — knowing what a stain looks like helps
    it avoid calling one a crack — but the detections are discarded rather than
    scored. Counting stains would inflate severity totals with something no
    structural engineer calls a defect.

    This test exists so nobody 'helpfully' adds the alias later without
    reading why it is missing.
    """
    assert map_class_name("stain") is None
    assert map_class_name("staining") is None


def test_normalized_area_is_box_geometry() -> None:
    det = RawDetection(DefectClass.CRACK, 0.9, (0.1, 0.1, 0.25, 0.40))
    assert det.normalized_area == pytest.approx(0.10)


# --- single-media inference ----------------------------------------------

def test_detect_image_persists_rows(
    client: TestClient, uploaded_image: dict, stub: StubDetector
) -> None:
    resp = client.post(f"/api/v1/media/{uploaded_image['id']}/detect")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["detection_count"] == 2
    assert body["frames_analyzed"] == 1
    assert body["model_weights"] == "stub.pt"

    top = body["detections"][0]
    assert top["defect_class"] == "crack"
    assert top["confidence"] == pytest.approx(0.91)
    assert top["bbox_x"] == pytest.approx(0.10)
    assert top["bbox_width"] == pytest.approx(0.30)
    # Geometry, then scoring — Phase 3 populates severity as rows are written,
    # so nothing reaches the dashboard unscored. (This assertion previously
    # required severity to be null, which was the Phase 2 invariant D-013
    # described; D-018's scoring engine deliberately supersedes it.)
    assert top["normalized_area"] == pytest.approx(0.12)
    assert top["class_weight"] == 1.0
    assert top["severity_score"] == pytest.approx(0.12 * 0.91 * 1.0)
    assert top["severity_band"] is not None

    assert stub.calls == [("image", stub.calls[0][1])]
    assert stub.calls[0][0] == "image"


def test_detect_marks_media_processed(
    client: TestClient, uploaded_image: dict, stub: StubDetector
) -> None:
    assert uploaded_image["processed"] is False
    client.post(f"/api/v1/media/{uploaded_image['id']}/detect")
    after = client.get(f"/api/v1/media/{uploaded_image['id']}").json()
    assert after["processed"] is True


def test_rerunning_replaces_rather_than_accumulates(
    client: TestClient, uploaded_image: dict, stub: StubDetector
) -> None:
    """A second pass after a model upgrade must not leave two generations."""
    for _ in range(3):
        client.post(f"/api/v1/media/{uploaded_image['id']}/detect")

    listed = client.get(f"/api/v1/media/{uploaded_image['id']}/detections").json()
    assert len(listed) == 2


def test_detections_sorted_by_confidence(
    client: TestClient, uploaded_image: dict, stub: StubDetector
) -> None:
    client.post(f"/api/v1/media/{uploaded_image['id']}/detect")
    listed = client.get(f"/api/v1/media/{uploaded_image['id']}/detections").json()
    confidences = [d["confidence"] for d in listed]
    assert confidences == sorted(confidences, reverse=True)


def test_empty_result_is_valid(
    client: TestClient, uploaded_image: dict
) -> None:
    """A clean asset is a real outcome, not an error."""
    inference.set_detector(StubDetector(detections=[]))
    try:
        resp = client.post(f"/api/v1/media/{uploaded_image['id']}/detect")
        assert resp.status_code == 200
        assert resp.json()["detection_count"] == 0
        after = client.get(f"/api/v1/media/{uploaded_image['id']}").json()
        assert after["processed"] is True
    finally:
        inference.set_detector(None)


def test_video_detections_carry_frame_index(
    client: TestClient, inspection: dict
) -> None:
    detector = StubDetector(
        detections=[
            RawDetection(DefectClass.CRACK, 0.8, (0.1, 0.1, 0.2, 0.2), frame_index=0),
            RawDetection(DefectClass.CRACK, 0.7, (0.3, 0.3, 0.2, 0.2), frame_index=15),
        ],
        frames=2,
    )
    inference.set_detector(detector)
    try:
        upload = client.post(
            f"/api/v1/inspections/{inspection['id']}/uploads",
            files=[("files", ("span.mp4", make_mp4(frames=30), "video/mp4"))],
        ).json()["results"][0]["media_file"]

        resp = client.post(f"/api/v1/media/{upload['id']}/detect")
        assert resp.status_code == 200
        body = resp.json()
        assert body["frames_analyzed"] == 2
        assert sorted(d["frame_index"] for d in body["detections"]) == [0, 15]
        assert detector.calls[0][0] == "video"
    finally:
        inference.set_detector(None)


def test_detect_unknown_media_is_404(client: TestClient, stub: StubDetector) -> None:
    import uuid

    assert client.post(f"/api/v1/media/{uuid.uuid4()}/detect").status_code == 404


# --- inspection-level dispatch -------------------------------------------

def test_inspection_detect_processes_all_media(
    client: TestClient, inspection: dict, stub: StubDetector
) -> None:
    client.post(
        f"/api/v1/inspections/{inspection['id']}/uploads",
        files=[
            ("files", ("a.jpg", make_jpeg(), "image/jpeg")),
            ("files", ("b.jpg", make_jpeg(), "image/jpeg")),
        ],
    )

    resp = client.post(f"/api/v1/inspections/{inspection['id']}/detect")
    assert resp.status_code == 202
    assert resp.json()["queued_media"] == 2

    # TestClient runs background tasks before returning, so status has settled.
    after = client.get(f"/api/v1/inspections/{inspection['id']}").json()
    assert after["status"] == "completed"

    detections = client.get(
        f"/api/v1/inspections/{inspection['id']}/detections"
    ).json()
    assert len(detections) == 4  # 2 files x 2 boxes


def test_inspection_detect_skips_already_processed(
    client: TestClient, inspection: dict, uploaded_image: dict, stub: StubDetector
) -> None:
    client.post(f"/api/v1/media/{uploaded_image['id']}/detect")

    resp = client.post(f"/api/v1/inspections/{inspection['id']}/detect")
    assert resp.json()["queued_media"] == 0
    assert resp.json()["already_processed"] == 1
    assert "reprocess=true" in resp.json()["detail"]


def test_inspection_detect_reprocess_flag(
    client: TestClient, inspection: dict, uploaded_image: dict, stub: StubDetector
) -> None:
    client.post(f"/api/v1/media/{uploaded_image['id']}/detect")
    resp = client.post(
        f"/api/v1/inspections/{inspection['id']}/detect", params={"reprocess": "true"}
    )
    assert resp.json()["queued_media"] == 1


def test_inspection_with_no_media_reports_nothing_to_do(
    client: TestClient, inspection: dict, stub: StubDetector
) -> None:
    resp = client.post(f"/api/v1/inspections/{inspection['id']}/detect")
    assert resp.status_code == 202
    assert resp.json()["queued_media"] == 0
    assert "no media uploaded" in resp.json()["detail"]


def test_failed_inference_marks_inspection_failed(
    client: TestClient, inspection: dict
) -> None:
    """A partial run must not report COMPLETED — that understates defect counts."""

    class ExplodingDetector(StubDetector):
        def analyze_image(self, path):
            raise RuntimeError("model exploded")

    client.post(
        f"/api/v1/inspections/{inspection['id']}/uploads",
        files=[("files", ("a.jpg", make_jpeg(), "image/jpeg"))],
    )
    inference.set_detector(ExplodingDetector())
    try:
        client.post(f"/api/v1/inspections/{inspection['id']}/detect")
        after = client.get(f"/api/v1/inspections/{inspection['id']}").json()
        assert after["status"] == "failed"
    finally:
        inference.set_detector(None)


# --- summary and introspection -------------------------------------------

def test_summary_counts_by_class(
    client: TestClient, inspection: dict, uploaded_image: dict, stub: StubDetector
) -> None:
    client.post(f"/api/v1/media/{uploaded_image['id']}/detect")

    summary = client.get(
        f"/api/v1/inspections/{inspection['id']}/detections/summary"
    ).json()
    assert summary["media_total"] == 1
    assert summary["media_processed"] == 1
    assert summary["detection_total"] == 2
    assert {c["defect_class"]: c["count"] for c in summary["by_class"]} == {
        "crack": 1,
        "corrosion": 1,
    }


def test_detector_endpoint_reports_active_weights(
    client: TestClient, stub: StubDetector
) -> None:
    body = client.get("/api/v1/detector").json()
    assert body["weights"] == "stub.pt"
    assert set(body["defect_classes"]) == {
        "crack",
        "corrosion",
        "surface_damage",
        "missing_component",
    }
