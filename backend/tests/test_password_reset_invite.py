from app.core.security import create_purpose_token


def _login(client, email, password):
    return client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )


def test_reset_request_no_enumeration(client):
    # both known and unknown emails return 202
    assert (
        client.post(
            "/api/auth/password-reset/request",
            json={"email": "registrar@consulthub.local"},
        ).status_code
        == 202
    )
    assert (
        client.post(
            "/api/auth/password-reset/request",
            json={"email": "nobody@nowhere.local"},
        ).status_code
        == 202
    )


def test_reset_confirm_flow(client):
    token = create_purpose_token(3, "reset", 60)  # registrar is user id 3
    # too short
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "short"},
        ).status_code
        == 422
    )
    # bad token
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": "garbage", "new_password": "newpass123"},
        ).status_code
        == 400
    )
    # valid
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "newpass123"},
        ).status_code
        == 204
    )
    assert (
        _login(client, "registrar@consulthub.local", "consulthub").status_code
        == 401
    )
    assert (
        _login(client, "registrar@consulthub.local", "newpass123").status_code
        == 200
    )


def test_access_token_not_valid_as_reset(client, registrar):
    at = registrar["Authorization"].split(" ", 1)[1]
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": at, "new_password": "whatever12"},
    )
    assert r.status_code == 400


def test_invite_and_accept(client, admin):
    r = client.post(
        "/api/users/invite",
        headers=admin,
        json={
            "full_name": "Invited Nurse",
            "email": "invited@consulthub.local",
            "role": "nurse",
        },
    )
    assert r.status_code == 201
    assert r.json()["institution_id"] == 1
    uid = r.json()["id"]
    # cannot log in before accepting (random placeholder password)
    assert (
        _login(client, "invited@consulthub.local", "consulthub").status_code
        == 401
    )
    token = create_purpose_token(uid, "invite", 60)
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "welcome123"},
        ).status_code
        == 204
    )
    assert (
        _login(client, "invited@consulthub.local", "welcome123").status_code
        == 200
    )


def test_invite_requires_admin(client, registrar):
    r = client.post(
        "/api/users/invite",
        headers=registrar,
        json={"full_name": "x", "email": "x@y.local", "role": "nurse"},
    )
    assert r.status_code == 403


def test_invite_cannot_grant_super_admin(client, admin):
    r = client.post(
        "/api/users/invite",
        headers=admin,
        json={
            "full_name": "x",
            "email": "x2@y.local",
            "role": "super_admin",
        },
    )
    assert r.status_code == 403
