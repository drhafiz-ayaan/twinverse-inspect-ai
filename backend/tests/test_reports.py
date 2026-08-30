"""PDF report export."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.models import DefectClass
from app.services import inference
from app.services.inference import RawDetection
from tests.conftest import make_jpeg
from tests.test_detections import StubDetector


@pytest.fixture
def analysed(client: TestClient, inspection: dict) -> dict:
    inference.set_detector(
        StubDetector(
            detections=[
                RawDetection(DefectClass.CRACK, 0.80, (0.1, 0.1, 0.25, 0.15)),
                RawDetection(DefectClass.CRACK, 0.35, (0.6, 0.2, 0.05, 0.04)),
            ]
        )
    )
    try:
        client.post(
            f"/api/v1/inspections/{inspection['id']}/uploads",
            files=[("files", ("pier-north.jpg", make_jpeg(), "image/jpeg"))],
        )
        client.post(f"/api/v1/inspections/{inspection['id']}/detect")
        yield inspection
    finally:
        inference.set_detector(None)


def test_report_returns_a_pdf(client: TestClient, analysed: dict) -> None:
    resp = client.get(f"/api/v1/inspections/{analysed['id']}/report.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # Real PDF, not an error page with the wrong content type.
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > 2000


def test_report_filename_is_descriptive_and_safe(
    client: TestClient, analysed: dict
) -> None:
    resp = client.get(f"/api/v1/inspections/{analysed['id']}/report.pdf")
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert disposition.endswith('.pdf"')
    assert "test-bridge" in disposition


def test_report_filename_strips_header_injection(client: TestClient, db) -> None:
    """Asset names are user input and land in a response header.

    A quote or newline there is a header-injection vector, so the slug keeps
    only an alphanumeric allowlist rather than trying to escape.
    """
    from app.api.routers.reports import _filename

    name = _filename('Bad"\r\nX-Injected: yes', "t")
    assert '"' not in name and "\r" not in name and "\n" not in name
    assert name.endswith(".pdf")


def test_report_works_with_no_detections(
    client: TestClient, inspection: dict
) -> None:
    """An inspection with nothing found is a valid outcome, not an error."""
    resp = client.get(f"/api/v1/inspections/{inspection['id']}/report.pdf")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")


def test_report_for_unknown_inspection_is_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/inspections/{uuid.uuid4()}/report.pdf")
    assert resp.status_code == 404


def test_report_states_its_limitations(client: TestClient, analysed: dict) -> None:
    """The limitations section is load-bearing, not decoration.

    A report listing defects without the detector's false-positive rate invites
    the reader to treat it as an authoritative survey. Extracting text from the
    PDF keeps that section from being quietly dropped in a redesign.
    """
    from pypdf import PdfReader
    import io

    resp = client.get(f"/api/v1/inspections/{analysed['id']}/report.pdf")
    text = " ".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(resp.content)).pages
    ).lower()

    assert "limitations" in text
    assert "relative" in text
    assert "false positive" in text
    assert "qualified engineer" in text
    assert "only cracks" in text
    # The formula must be on the page — D-004 commits to showing it.
    assert "normalized_area" in text
