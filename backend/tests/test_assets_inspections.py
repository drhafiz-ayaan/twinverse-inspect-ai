"""Asset and inspection CRUD."""

import uuid

from fastapi.testclient import TestClient


def test_create_and_fetch_asset(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/assets",
        json={"name": "Riverside Viaduct", "asset_type": "bridge"},
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["name"] == "Riverside Viaduct"
    assert created["asset_type"] == "bridge"

    fetched = client.get(f"/api/v1/assets/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_asset_rejects_out_of_range_latitude(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/assets",
        json={"name": "Bad Coords", "asset_type": "dam", "latitude": 120.0},
    )
    assert resp.status_code == 422


def test_missing_asset_is_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/assets/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_list_assets_filters_by_type(client: TestClient) -> None:
    client.post("/api/v1/assets", json={"name": "B1", "asset_type": "bridge"})
    client.post("/api/v1/assets", json={"name": "D1", "asset_type": "dam"})

    bridges = client.get("/api/v1/assets", params={"asset_type": "bridge"}).json()
    assert [a["name"] for a in bridges] == ["B1"]


def test_patch_asset_updates_only_supplied_fields(
    client: TestClient, asset: dict
) -> None:
    resp = client.patch(
        f"/api/v1/assets/{asset['id']}", json={"location": "Relocated"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"] == "Relocated"
    assert body["name"] == asset["name"]  # untouched


def test_inspection_requires_existing_asset(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/inspections",
        json={"asset_id": str(uuid.uuid4()), "title": "Orphan"},
    )
    assert resp.status_code == 404


def test_inspection_defaults_to_pending(client: TestClient, inspection: dict) -> None:
    assert inspection["status"] == "pending"


def test_list_inspections_includes_media_count(
    client: TestClient, inspection: dict
) -> None:
    listed = client.get("/api/v1/inspections").json()
    assert len(listed) == 1
    assert listed[0]["media_count"] == 0


def test_deleting_asset_cascades_to_inspections(
    client: TestClient, admin_client: TestClient, asset: dict, inspection: dict
) -> None:
    """Asset deletion is admin-only — it cascades to every inspection under it."""
    assert admin_client.delete(f"/api/v1/assets/{asset['id']}").status_code == 204
    assert client.get(f"/api/v1/inspections/{inspection['id']}").status_code == 404
