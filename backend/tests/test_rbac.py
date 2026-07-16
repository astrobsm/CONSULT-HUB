def test_non_admin_cannot_list_users(client, registrar):
    assert client.get("/api/users", headers=registrar).status_code == 403


def test_admin_lists_own_institution_only(client, admin, other_tenant):
    users = client.get("/api/users", headers=admin).json()
    assert all(u["institution_id"] == 1 for u in users)


def test_institution_admin_cannot_grant_super_admin(client, admin):
    r = client.post(
        "/api/users",
        headers=admin,
        json={
            "full_name": "Evil",
            "email": "evil@consulthub.local",
            "password": "password1",
            "role": "super_admin",
        },
    )
    assert r.status_code == 403


def test_super_admin_can_create_super_admin(client, superadmin):
    r = client.post(
        "/api/users",
        headers=superadmin,
        json={
            "full_name": "Root2",
            "email": "root2@consulthub.local",
            "password": "password1",
            "role": "super_admin",
        },
    )
    assert r.status_code == 201


def test_admin_cannot_see_other_tenant_user(client, admin, superadmin):
    other = client.post(
        "/api/users",
        headers=superadmin,
        json={
            "full_name": "Other",
            "email": "other@x.local",
            "password": "password1",
            "role": "registrar",
            "institution_id": 999,
        },
    ).json()
    assert client.get(f"/api/users/{other['id']}", headers=admin).status_code == 404


def test_cannot_deactivate_self(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    r = client.patch(
        f"/api/users/{me['id']}", headers=admin, json={"is_active": False}
    )
    assert r.status_code == 400


def test_only_super_admin_creates_institution(client, admin, superadmin):
    assert (
        client.post(
            "/api/institutions", headers=admin, json={"name": "X", "code": "XX"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/institutions",
            headers=superadmin,
            json={"name": "St Mary", "code": "STMARY"},
        ).status_code
        == 201
    )
