# A 1x1 transparent PNG.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15"
    "c4890000000d4944415478da6360000002000154a24f6d0000000049454e44"
    "ae426082"
)


def test_user_appearance_defaults_and_update(client, registrar):
    me = client.get("/api/auth/me", headers=registrar).json()
    assert me["theme"] == "system"
    assert me["accent"] == "blue"
    assert me["font_family"] == "system"

    r = client.patch(
        "/api/auth/me",
        headers=registrar,
        json={"theme": "dark", "accent": "teal", "font_family": "serif"},
    )
    assert r.status_code == 200
    assert r.json()["theme"] == "dark"
    assert (
        client.get("/api/auth/me", headers=registrar).json()["accent"]
        == "teal"
    )


def test_institution_branding_update(client, admin, registrar):
    iid = client.get("/api/institutions", headers=admin).json()[0]["id"]
    r = client.patch(
        f"/api/institutions/{iid}",
        headers=admin,
        json={"motto": "Care first", "primary_color": "#0d9488"},
    )
    assert r.status_code == 200
    assert r.json()["motto"] == "Care first"
    # non-admin cannot update branding
    assert (
        client.patch(
            f"/api/institutions/{iid}", headers=registrar, json={"motto": "x"}
        ).status_code
        == 403
    )


def test_logo_upload_serve_and_validation(client, admin, registrar):
    iid = client.get("/api/institutions", headers=admin).json()[0]["id"]
    assert (
        client.get(f"/api/institutions/{iid}", headers=admin).json()["has_logo"]
        is False
    )
    up = client.post(
        f"/api/institutions/{iid}/logo",
        headers=admin,
        files={"file": ("logo.png", PNG, "image/png")},
    )
    assert up.status_code == 200
    assert up.json()["has_logo"] is True

    dl = client.get(f"/api/institutions/{iid}/logo", headers=registrar)
    assert dl.status_code == 200
    assert dl.content == PNG

    bad = client.post(
        f"/api/institutions/{iid}/logo",
        headers=admin,
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert bad.status_code == 422


def test_institution_tenant_isolation(client, admin, other_tenant):
    iid = client.get("/api/institutions", headers=admin).json()[0]["id"]
    # other_tenant is a registrar in inst 999 (see conftest) -> not an admin,
    # but even a GET is scoped: it's not their institution.
    assert (
        client.get(f"/api/institutions/{iid}", headers=other_tenant).status_code
        == 404
    )
