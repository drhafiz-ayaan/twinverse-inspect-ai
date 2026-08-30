"""Authentication and role-based access control."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.db.models import UserRole
from tests.conftest import PASSWORD, ROLE_EMAILS


# --- password hashing ----------------------------------------------------

def test_hash_verifies_and_is_salted() -> None:
    a = security.hash_password("correct horse battery staple")
    b = security.hash_password("correct horse battery staple")
    assert a != b, "identical passwords must not produce identical hashes"
    assert security.verify_password("correct horse battery staple", a)
    assert not security.verify_password("wrong", a)


def test_overlong_password_is_rejected_not_truncated() -> None:
    """bcrypt silently truncates past 72 bytes.

    Truncating turns a long passphrase into a shorter effective secret without
    telling anyone, so two different long passwords could authenticate each
    other. Reject instead.
    """
    with pytest.raises(ValueError):
        security.hash_password("x" * 73)


def test_malformed_stored_hash_fails_closed() -> None:
    assert security.verify_password("anything", "not-a-bcrypt-hash") is False


# --- tokens --------------------------------------------------------------

def test_token_roundtrip() -> None:
    uid = uuid.uuid4()
    claims = security.decode_access_token(
        security.create_access_token(uid, "inspector")
    )
    assert claims is not None
    assert claims["sub"] == str(uid)
    assert claims["role"] == "inspector"


@pytest.mark.parametrize(
    "token", ["", "garbage", "a.b.c", "Bearer x"],
)
def test_malformed_tokens_are_rejected(token) -> None:
    assert security.decode_access_token(token) is None


def test_token_signed_with_another_key_is_rejected() -> None:
    """The signature must actually be checked, not just the shape."""
    import jwt

    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "admin", "typ": "access"},
        "a-different-secret",
        algorithm="HS256",
    )
    assert security.decode_access_token(forged) is None


# --- login ---------------------------------------------------------------

def test_login_returns_a_usable_token(anon_client: TestClient) -> None:
    resp = anon_client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[UserRole.INSPECTOR], "password": PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "inspector"

    me = anon_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == ROLE_EMAILS[UserRole.INSPECTOR]


def test_wrong_password_and_unknown_user_are_indistinguishable(
    anon_client: TestClient,
) -> None:
    """Neither response may reveal whether an address is registered."""
    wrong = anon_client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[UserRole.VIEWER], "password": "nope"},
    )
    unknown = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "nope"},
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_login_is_case_insensitive_on_email(anon_client: TestClient) -> None:
    resp = anon_client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[UserRole.ADMIN].upper(), "password": PASSWORD},
    )
    assert resp.status_code == 200


# --- the baseline guard --------------------------------------------------

@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/assets"),
        ("get", "/api/v1/inspections"),
        ("post", "/api/v1/assets"),
        ("get", "/api/v1/detector"),
        ("get", "/api/v1/severity/model"),
    ],
)
def test_api_requires_authentication(anon_client: TestClient, method, path) -> None:
    kwargs = {"json": {}} if method == "post" else {}
    resp = getattr(anon_client, method)(path, **kwargs)
    # 401 must come from the auth guard, before any body validation — an
    # unauthenticated caller should never learn whether their payload was valid.
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_health_stays_public(anon_client: TestClient) -> None:
    """An orchestrator must be able to probe without credentials."""
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/health/ready").status_code == 200


def test_garbage_token_is_401_not_500(anon_client: TestClient) -> None:
    resp = anon_client.get(
        "/api/v1/assets", headers={"Authorization": "Bearer not-a-token"}
    )
    assert resp.status_code == 401


def test_token_for_deleted_user_stops_working(
    admin_client: TestClient, anon_client: TestClient
) -> None:
    """A valid signature is not enough — the account must still exist."""
    created = admin_client.post(
        "/api/v1/auth/users",
        json={"email": "temp@example.com", "password": "temp-password-1", "role": "viewer"},
    ).json()

    token = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "temp@example.com", "password": "temp-password-1"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert anon_client.get("/api/v1/assets", headers=headers).status_code == 200

    admin_client.patch(
        f"/api/v1/auth/users/{created['id']}", json={"is_active": False}
    )
    assert anon_client.get("/api/v1/assets", headers=headers).status_code == 401


def test_role_is_read_from_the_database_not_the_token(
    admin_client: TestClient, anon_client: TestClient
) -> None:
    """A demotion must take effect immediately, not when the token expires."""
    created = admin_client.post(
        "/api/v1/auth/users",
        json={"email": "demote@example.com", "password": "temp-password-1",
              "role": "inspector"},
    ).json()
    token = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "demote@example.com", "password": "temp-password-1"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"name": "Before", "asset_type": "bridge"}
    assert anon_client.post(
        "/api/v1/assets", json=payload, headers=headers
    ).status_code == 201

    admin_client.patch(f"/api/v1/auth/users/{created['id']}", json={"role": "viewer"})

    # Same token, now insufficient.
    assert anon_client.post(
        "/api/v1/assets", json=payload, headers=headers
    ).status_code == 403


# --- role enforcement ----------------------------------------------------

def test_viewer_can_read_but_not_write(
    viewer_client: TestClient, client: TestClient
) -> None:
    assert viewer_client.get("/api/v1/assets").status_code == 200
    resp = viewer_client.post(
        "/api/v1/assets", json={"name": "Nope", "asset_type": "bridge"}
    )
    assert resp.status_code == 403
    assert "inspector" in resp.json()["detail"]


def test_inspector_can_write_but_not_delete_assets(
    client: TestClient, asset: dict
) -> None:
    assert client.patch(
        f"/api/v1/assets/{asset['id']}", json={"location": "Moved"}
    ).status_code == 200
    assert client.delete(f"/api/v1/assets/{asset['id']}").status_code == 403


def test_only_admin_manages_users(
    client: TestClient, viewer_client: TestClient, admin_client: TestClient
) -> None:
    body = {"email": "new@example.com", "password": "new-password-1"}
    assert viewer_client.post("/api/v1/auth/users", json=body).status_code == 403
    assert client.post("/api/v1/auth/users", json=body).status_code == 403
    assert admin_client.post("/api/v1/auth/users", json=body).status_code == 201


def test_duplicate_email_is_409(admin_client: TestClient) -> None:
    body = {"email": "dupe@example.com", "password": "some-password-1"}
    assert admin_client.post("/api/v1/auth/users", json=body).status_code == 201
    assert admin_client.post("/api/v1/auth/users", json=body).status_code == 409


def test_new_users_default_to_viewer(admin_client: TestClient) -> None:
    """Least privilege: an account with no role stated gets the weakest one."""
    created = admin_client.post(
        "/api/v1/auth/users",
        json={"email": "default@example.com", "password": "some-password-1"},
    ).json()
    assert created["role"] == "viewer"


def test_cannot_disable_the_last_admin(admin_client: TestClient) -> None:
    """Otherwise an admin can lock everyone out of user management."""
    me = admin_client.get("/api/v1/auth/me").json()
    resp = admin_client.patch(
        f"/api/v1/auth/users/{me['id']}", json={"is_active": False}
    )
    assert resp.status_code == 409
    assert "last active admin" in resp.json()["detail"]


def test_can_demote_an_admin_when_another_remains(admin_client: TestClient) -> None:
    second = admin_client.post(
        "/api/v1/auth/users",
        json={"email": "admin2@example.com", "password": "some-password-1",
              "role": "admin"},
    ).json()
    resp = admin_client.patch(
        f"/api/v1/auth/users/{second['id']}", json={"role": "viewer"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


def test_password_is_never_returned(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/auth/users",
        json={"email": "secret@example.com", "password": "some-password-1"},
    ).json()
    assert "password" not in created
    assert "hashed_password" not in created
    listed = admin_client.get("/api/v1/auth/users").json()
    assert all("hashed_password" not in u for u in listed)
