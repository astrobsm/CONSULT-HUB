import pytest

from app.core.security import create_purpose_token

MONDAY = "2026-07-20"


@pytest.fixture()
def portal_patient(client):
    """Activate patient 1 (Grace) for the portal and return {headers, id}."""
    from app.core.database import SessionLocal
    from app.models.entities import Patient

    db = SessionLocal()
    p = db.get(Patient, 1)
    p.email = "grace@example.com"
    db.commit()
    db.close()

    token = create_purpose_token(1, "portal", 60)
    assert (
        client.post(
            "/api/portal/set-password",
            json={"token": token, "password": "portalpass1"},
        ).status_code
        == 204
    )
    r = client.post(
        "/api/portal/login",
        data={"username": "grace@example.com", "password": "portalpass1"},
    )
    assert r.status_code == 200
    return {
        "headers": {"Authorization": f"Bearer {r.json()['access_token']}"},
        "id": 1,
    }


def _staff(client):
    tok = client.post(
        "/api/auth/login",
        data={"username": "registrar@consulthub.local", "password": "consulthub"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_activation_no_enumeration(client):
    from app.core.database import SessionLocal
    from app.models.entities import Patient

    db = SessionLocal()
    db.get(Patient, 1).email = "grace@example.com"
    db.commit()
    db.close()
    assert (
        client.post(
            "/api/portal/activate",
            json={"hospital_number": "MRN-100234", "email": "grace@example.com"},
        ).status_code
        == 202
    )
    assert (
        client.post(
            "/api/portal/activate",
            json={"hospital_number": "MRN-100234", "email": "wrong@x.com"},
        ).status_code
        == 202
    )


def test_portal_set_password_rejects_wrong_purpose(client):
    reset = create_purpose_token(1, "reset", 60)
    assert (
        client.post(
            "/api/portal/set-password",
            json={"token": reset, "password": "x12345678"},
        ).status_code
        == 400
    )


def test_login_bad_password(client, portal_patient):
    assert (
        client.post(
            "/api/portal/login",
            data={"username": "grace@example.com", "password": "nope"},
        ).status_code
        == 401
    )


def test_patient_token_rejected_on_staff_endpoints(client, portal_patient):
    h = portal_patient["headers"]
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.get("/api/consultations", headers=h).status_code == 401
    assert client.get("/api/users", headers=h).status_code == 401


def test_staff_token_rejected_on_portal(client):
    assert client.get("/api/portal/me", headers=_staff(client)).status_code == 401


def test_portal_me(client, portal_patient):
    r = client.get("/api/portal/me", headers=portal_patient["headers"])
    assert r.status_code == 200
    assert r.json()["hospital_number"] == "MRN-100234"


def test_self_book_forces_own_patient(client, portal_patient):
    h = portal_patient["headers"]
    cid = client.get("/api/portal/clinics", headers=h).json()[0]["id"]
    slot = client.get(
        f"/api/portal/clinics/{cid}/availability?date={MONDAY}", headers=h
    ).json()["stations"][0]["free_slots"][0]
    b = client.post(
        "/api/portal/appointments",
        headers=h,
        json={"clinic_id": cid, "slot_start": slot, "appointment_type": "review"},
    )
    assert b.status_code == 201
    assert b.json()["patient_id"] == 1
    mine = client.get("/api/portal/appointments", headers=h).json()
    assert all(a["patient_id"] == 1 for a in mine)


def test_cannot_touch_other_patients_appointment(client, portal_patient):
    h = portal_patient["headers"]
    staff = _staff(client)
    cid = client.get("/api/portal/clinics", headers=h).json()[0]["id"]
    slot = client.get(
        f"/api/clinics/{cid}/availability?date={MONDAY}", headers=staff
    ).json()["stations"][1]["free_slots"][0]
    other = client.post(
        "/api/appointments",
        headers=staff,
        json={
            "clinic_id": cid,
            "patient_id": 2,
            "slot_start": slot,
            "appointment_type": "review",
        },
    ).json()
    assert (
        client.post(
            f"/api/portal/appointments/{other['id']}/cancel", headers=h
        ).status_code
        == 404
    )


def test_cross_institution_clinic_hidden(client, portal_patient, superadmin):
    h = portal_patient["headers"]
    oc = client.post(
        "/api/clinics", headers=superadmin, json={"name": "Other Inst"}
    )
    # superadmin has no institution, so the clinic is created with inst=None;
    # ensure it's not the patient's institution and thus not visible.
    if oc.status_code == 201:
        cid = oc.json()["id"]
        assert (
            client.get(
                f"/api/portal/clinics/{cid}/availability?date={MONDAY}",
                headers=h,
            ).status_code
            == 404
        )
