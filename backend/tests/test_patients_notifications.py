def test_patient_computed_fields(client, registrar):
    r = client.post(
        "/api/patients",
        headers=registrar,
        json={
            "hospital_number": "MRN-T1",
            "full_name": "Test One",
            "date_of_birth": "2000-01-01",
            "sex": "Male",
            "weight_kg": 80,
            "height_cm": 200,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["bmi"] == 20.0  # 80 / 2.0^2
    assert body["age"] and body["age"] >= 25


def test_patient_search(client, registrar):
    assert (
        client.get("/api/patients?search=grace", headers=registrar)
        .json()[0]["full_name"]
        == "Grace Adeyemi"
    )


def test_consult_rejects_cross_tenant_patient(client, registrar, superadmin):
    # patient in another institution
    # (super admin creates a user there, but patients are created by that user)
    client.post(
        "/api/users",
        headers=superadmin,
        json={
            "full_name": "Other Reg",
            "email": "otherreg@x.local",
            "password": "consulthub",
            "role": "registrar",
            "institution_id": 999,
        },
    )
    other = {
        "Authorization": "Bearer "
        + client.post(
            "/api/auth/login",
            data={"username": "otherreg@x.local", "password": "consulthub"},
        ).json()["access_token"]
    }
    pid = client.post(
        "/api/patients",
        headers=other,
        json={"hospital_number": "MRN-OT", "full_name": "Foreign Patient"},
    ).json()["id"]
    # registrar (inst 1) cannot reference inst-999 patient
    r = client.post(
        "/api/consultations",
        headers=registrar,
        json={
            "patient_id": pid,
            "reason": "x",
            "priority": "routine",
            "consultation_type": "ward",
        },
    )
    assert r.status_code == 422


def test_status_change_notifies_requester_not_actor(
    client, registrar, admin
):
    cid = client.post(
        "/api/consultations",
        headers=registrar,
        json={"reason": "x", "priority": "urgent", "consultation_type": "ward"},
    ).json()["id"]
    # admin acknowledges -> registrar (requester) notified, admin not
    client.post(
        f"/api/consultations/{cid}/transition",
        headers=admin,
        json={"to_status": "acknowledged"},
    )
    reg_notifs = client.get("/api/notifications", headers=registrar).json()
    assert any(n["kind"] == "status_change" for n in reg_notifs)
    admin_notifs = client.get("/api/notifications", headers=admin).json()
    assert all(n["kind"] != "status_change" for n in admin_notifs)


def test_message_notifies_participants_and_mark_read(client, registrar, admin):
    cid = client.post(
        "/api/consultations",
        headers=registrar,
        json={"reason": "x", "priority": "urgent", "consultation_type": "ward"},
    ).json()["id"]
    # admin posts -> registrar (requester) gets a message notification
    client.post(
        f"/api/consultations/{cid}/messages",
        headers=admin,
        json={"body": "please review"},
    )
    unread = client.get(
        "/api/notifications/unread-count", headers=registrar
    ).json()["unread"]
    assert unread >= 1
    client.post("/api/notifications/read-all", headers=registrar)
    assert (
        client.get("/api/notifications/unread-count", headers=registrar).json()[
            "unread"
        ]
        == 0
    )


def test_message_tenant_isolation(client, registrar, other_tenant):
    cid = client.post(
        "/api/consultations",
        headers=registrar,
        json={"reason": "x", "priority": "urgent", "consultation_type": "ward"},
    ).json()["id"]
    assert (
        client.get(
            f"/api/consultations/{cid}/messages", headers=other_tenant
        ).status_code
        == 404
    )
