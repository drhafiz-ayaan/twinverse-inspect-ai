"""Media ingest — the Phase 1 critical path."""

import hashlib
import uuid

import httpx
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services import storage
from tests.conftest import make_jpeg, make_mp4, make_png


def _upload(client: TestClient, inspection_id: str, files: list) -> httpx.Response:
    return client.post(f"/api/v1/inspections/{inspection_id}/uploads", files=files)


def test_image_upload_stores_object_and_row(
    client: TestClient, inspection: dict
) -> None:
    payload = make_jpeg(width=100, height=80)
    resp = _upload(
        client,
        inspection["id"],
        [("files", ("deck.jpg", payload, "image/jpeg"))],
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["accepted_count"] == 1
    assert body["rejected_count"] == 0

    record = body["results"][0]["media_file"]
    assert record["media_type"] == "image"
    assert record["size_bytes"] == len(payload)
    assert record["checksum_sha256"] == hashlib.sha256(payload).hexdigest()
    assert record["width"] == 100
    assert record["height"] == 80
    assert record["processed"] is False

    # The bytes really are in the bucket, and they are the bytes we sent.
    stored = storage.get_client().get_object(
        Bucket=settings.s3_bucket, Key=record["storage_key"]
    )["Body"].read()
    assert stored == payload


def test_video_upload_probes_duration_and_fps(
    client: TestClient, inspection: dict
) -> None:
    payload = make_mp4(frames=20, width=64, height=48, fps=10)
    resp = _upload(
        client,
        inspection["id"],
        [("files", ("flyover.mp4", payload, "video/mp4"))],
    )

    assert resp.status_code == 201, resp.text
    record = resp.json()["results"][0]["media_file"]
    assert record["media_type"] == "video"
    assert record["frame_count"] == 20
    assert record["fps"] == 10.0
    assert record["duration_seconds"] == 2.0
    assert record["width"] == 64
    assert record["height"] == 48


def test_unsupported_content_type_is_rejected(
    client: TestClient, inspection: dict
) -> None:
    resp = _upload(
        client,
        inspection["id"],
        [("files", ("notes.pdf", b"%PDF-1.4 fake", "application/pdf"))],
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["accepted_count"] == 0
    assert body["rejected_count"] == 1
    assert "not accepted" in body["results"][0]["error"]


def test_oversized_image_is_rejected(
    client: TestClient, inspection: dict, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "max_image_bytes", 128)
    resp = _upload(
        client,
        inspection["id"],
        [("files", ("big.jpg", make_jpeg(200, 200), "image/jpeg"))],
    )
    assert resp.status_code == 400
    assert "128 byte limit" in resp.json()["results"][0]["error"]


def test_empty_file_is_rejected(client: TestClient, inspection: dict) -> None:
    resp = _upload(
        client, inspection["id"], [("files", ("empty.jpg", b"", "image/jpeg"))]
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["results"][0]["error"]


def test_batch_isolates_failures(client: TestClient, inspection: dict) -> None:
    """One bad file must not reject the whole batch."""
    resp = _upload(
        client,
        inspection["id"],
        [
            ("files", ("good1.jpg", make_jpeg(), "image/jpeg")),
            ("files", ("bad.pdf", b"nope", "application/pdf")),
            ("files", ("good2.png", make_png(), "image/png")),
        ],
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["accepted_count"] == 2
    assert body["rejected_count"] == 1

    by_name = {r["filename"]: r for r in body["results"]}
    assert by_name["good1.jpg"]["accepted"] is True
    assert by_name["good2.png"]["accepted"] is True
    assert by_name["bad.pdf"]["accepted"] is False


def test_upload_to_unknown_inspection_is_404(client: TestClient) -> None:
    resp = _upload(
        client, str(uuid.uuid4()), [("files", ("x.jpg", make_jpeg(), "image/jpeg"))]
    )
    assert resp.status_code == 404


def test_same_filename_twice_does_not_collide(
    client: TestClient, inspection: dict
) -> None:
    keys = []
    for _ in range(2):
        resp = _upload(
            client,
            inspection["id"],
            [("files", ("same.jpg", make_jpeg(), "image/jpeg"))],
        )
        assert resp.status_code == 201
        keys.append(resp.json()["results"][0]["media_file"]["storage_key"])
    assert keys[0] != keys[1]


def test_media_listing_and_presigned_download(
    client: TestClient, inspection: dict
) -> None:
    payload = make_jpeg()
    _upload(
        client, inspection["id"], [("files", ("a.jpg", payload, "image/jpeg"))]
    )

    listing = client.get(f"/api/v1/inspections/{inspection['id']}/media")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    url = items[0]["download_url"]

    # Follow the presigned URL out-of-band: it must serve the original bytes.
    downloaded = httpx.get(url, timeout=10)
    assert downloaded.status_code == 200
    assert downloaded.content == payload


def test_media_count_reflects_uploads(client: TestClient, inspection: dict) -> None:
    _upload(
        client,
        inspection["id"],
        [
            ("files", ("a.jpg", make_jpeg(), "image/jpeg")),
            ("files", ("b.jpg", make_jpeg(), "image/jpeg")),
        ],
    )
    listed = client.get("/api/v1/inspections").json()
    assert listed[0]["media_count"] == 2


def test_delete_media_removes_row_and_object(
    client: TestClient, inspection: dict
) -> None:
    resp = _upload(
        client, inspection["id"], [("files", ("gone.jpg", make_jpeg(), "image/jpeg"))]
    )
    record = resp.json()["results"][0]["media_file"]

    assert client.delete(f"/api/v1/media/{record['id']}").status_code == 204
    assert client.get(f"/api/v1/media/{record['id']}").status_code == 404

    client_s3 = storage.get_client()
    try:
        client_s3.head_object(Bucket=settings.s3_bucket, Key=record["storage_key"])
        raise AssertionError("object should have been deleted from the bucket")
    except client_s3.exceptions.ClientError as exc:
        assert exc.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}
