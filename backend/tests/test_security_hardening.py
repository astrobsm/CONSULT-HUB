"""Regression tests for the security-review hardening.

Covers: purpose tokens can't authenticate requests, password changes invalidate
outstanding tokens, reset tokens are single-use, non-super users must have an
institution, and brand-image uploads reject non-raster (SVG) content.
"""

from app.core.security import create_purpose_token


def _login(client, email="registrar@consulthub.local", password="consulthub"):
    r = client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    return r


def _bearer(r):
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- Purpose tokens are not access tokens ----

def test_reset_token_rejected_as_staff_access(client):
    # A password-reset purpose token must never authenticate a staff request.
    token = create_purpose_token(3, "reset", 60)  # registrar id 3
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.get("/api/users", headers=h).status_code == 401


def test_invite_token_rejected_as_staff_access(client):
    token = create_purpose_token(2, "invite", 60)
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_portal_purpose_token_rejected_as_staff(client):
    # sub=3 collides with a staff user id; the portal purpose token must still
    # be rejected on staff endpoints (typ != "staff").
    token = create_purpose_token(3, "portal", 60)
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_purpose_token_rejected_on_websocket(client):
    token = create_purpose_token(3, "reset", 60)
    try:
        with client.websocket_connect(f"/api/ws?token={token}"):
            assert False, "purpose token should not open the WS channel"
    except Exception:
        pass  # handshake rejected as expected


# ---- Password change invalidates outstanding tokens ----

def test_change_password_invalidates_old_token(client):
    old = _bearer(_login(client))
    assert client.get("/api/auth/me", headers=old).status_code == 200
    r = client.post(
        "/api/auth/change-password",
        headers=old,
        json={
            "current_password": "consulthub",
            "new_password": "brandnew123",
        },
    )
    assert r.status_code == 204
    # The token minted before the change no longer works.
    assert client.get("/api/auth/me", headers=old).status_code == 401
    # A fresh login with the new password does.
    fresh = _bearer(_login(client, password="brandnew123"))
    assert client.get("/api/auth/me", headers=fresh).status_code == 200


def test_reset_token_is_single_use(client):
    token = create_purpose_token(3, "reset", 60)
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "firstpass123"},
        ).status_code
        == 204
    )
    # Replaying the same reset token after it set a password is rejected.
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "secondpass123"},
        ).status_code
        == 400
    )


def test_reset_does_not_reactivate_deactivated_account(client, admin):
    # Deactivate the registrar (user id 3) via admin.
    assert (
        client.patch(
            "/api/users/3", headers=admin, json={"is_active": False}
        ).status_code
        == 200
    )
    token = create_purpose_token(3, "reset", 60)
    client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "resetpass123"},
    )
    # A plain reset must not silently re-activate the account.
    assert (
        _login(client, password="resetpass123").status_code == 401
    )


# ---- Tenant invariant: non-super users must have an institution ----

def test_non_super_user_requires_institution(client, superadmin):
    r = client.post(
        "/api/users",
        headers=superadmin,
        json={
            "full_name": "No Tenant",
            "email": "notenant@x.local",
            "password": "consulthub",
            "role": "registrar",
            # no institution_id
        },
    )
    assert r.status_code == 422


def test_super_admin_may_have_no_institution(client, superadmin):
    r = client.post(
        "/api/users",
        headers=superadmin,
        json={
            "full_name": "Root Two",
            "email": "root2@x.local",
            "password": "consulthub",
            "role": "super_admin",
        },
    )
    assert r.status_code == 201


# ---- Brand-image uploads reject non-raster content ----

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)
_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def test_logo_upload_rejects_svg(client, admin):
    # Spoof the content-type header as image/png; the byte sniff still rejects.
    r = client.post(
        "/api/institutions/1/logo",
        headers=admin,
        files={"file": ("x.svg", _SVG, "image/png")},
    )
    assert r.status_code == 422


def test_logo_upload_accepts_png_and_serves_nosniff(client, admin):
    r = client.post(
        "/api/institutions/1/logo",
        headers=admin,
        files={"file": ("logo.bin", _PNG, "application/octet-stream")},
    )
    assert r.status_code == 200
    got = client.get("/api/institutions/1/logo", headers=admin)
    assert got.status_code == 200
    assert got.headers.get("x-content-type-options") == "nosniff"
    assert got.headers["content-type"] == "image/png"
