def test_login_success(client):
    r = client.post(
        "/api/auth/login",
        data={"username": "admin@consulthub.local", "password": "consulthub"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "institution_admin"
    assert body["token_type"] == "bearer"


def test_login_bad_password(client):
    r = client.post(
        "/api/auth/login",
        data={"username": "admin@consulthub.local", "password": "nope"},
    )
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_self_registration_disabled(client):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "x", "email": "x@y.z", "password": "password1"},
    )
    assert r.status_code == 404


def test_change_password_flow(client, registrar):
    # wrong current
    assert (
        client.post(
            "/api/auth/change-password",
            headers=registrar,
            json={"current_password": "wrong", "new_password": "newpass123"},
        ).status_code
        == 400
    )
    # too short
    assert (
        client.post(
            "/api/auth/change-password",
            headers=registrar,
            json={"current_password": "consulthub", "new_password": "short"},
        ).status_code
        == 422
    )
    # success
    assert (
        client.post(
            "/api/auth/change-password",
            headers=registrar,
            json={
                "current_password": "consulthub",
                "new_password": "newpass123",
            },
        ).status_code
        == 204
    )
    # old fails, new works
    assert (
        client.post(
            "/api/auth/login",
            data={
                "username": "registrar@consulthub.local",
                "password": "consulthub",
            },
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            data={
                "username": "registrar@consulthub.local",
                "password": "newpass123",
            },
        ).status_code
        == 200
    )


def test_update_profile_keeps_role(client, registrar):
    r = client.patch(
        "/api/auth/me",
        headers=registrar,
        json={"full_name": "Dr. New Name"},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Dr. New Name"
    assert r.json()["role"] == "registrar"
