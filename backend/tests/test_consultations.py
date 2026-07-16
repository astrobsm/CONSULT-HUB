from datetime import datetime, timedelta, timezone


def _create(client, headers, **overrides):
    payload = {
        "reason": "Test consult",
        "priority": "urgent",
        "consultation_type": "ward",
    }
    payload.update(overrides)
    return client.post("/api/consultations", headers=headers, json=payload)


def test_create_requires_auth(client):
    assert _create(client, {}).status_code == 401


def test_create_injects_identity_and_tenant(client, registrar):
    r = _create(client, registrar)
    assert r.status_code == 201
    body = r.json()
    assert body["institution_id"] == 1
    assert body["requesting_user_id"] == 3  # registrar is seeded user id 3
    assert body["events"][0]["actor_user_id"] == 3


def test_workflow_and_invalid_transition(client, registrar):
    cid = _create(client, registrar).json()["id"]
    # submitted -> completed is invalid
    r = client.post(
        f"/api/consultations/{cid}/transition",
        headers=registrar,
        json={"to_status": "completed"},
    )
    assert r.status_code == 409
    # valid path to completed
    for s in ["acknowledged", "accepted", "seen", "completed"]:
        rr = client.post(
            f"/api/consultations/{cid}/transition",
            headers=registrar,
            json={"to_status": s},
        )
        assert rr.status_code == 200
    final = client.get(f"/api/consultations/{cid}", headers=registrar).json()
    assert final["status"] == "completed"
    assert final["acknowledged_at"] is not None
    assert final["completed_at"] is not None


def test_tenant_isolation(client, registrar, other_tenant):
    cid = _create(client, registrar).json()["id"]
    assert client.get("/api/consultations", headers=other_tenant).json() == []
    assert (
        client.get(
            f"/api/consultations/{cid}", headers=other_tenant
        ).status_code
        == 404
    )


def test_escalation_engine(client, registrar):
    from app.core.database import SessionLocal
    from app.core.escalation import run_escalations
    from app.models.consultation import Consultation

    cid = _create(
        client, registrar, required_response_minutes=15
    ).json()["id"]

    db = SessionLocal()
    con = db.get(Consultation, cid)
    con.created_at = datetime.now(timezone.utc) - timedelta(minutes=65)
    db.commit()
    fired = run_escalations(db, now=datetime.now(timezone.utc))
    levels = sorted(f["level"] for f in fired if f["consultation_id"] == cid)
    db.close()
    assert levels == [1, 2, 3]  # 15/30/60 crossed, 90 not yet

    got = client.get(f"/api/consultations/{cid}", headers=registrar).json()
    assert got["escalation_level"] == 3
    assert len(got["escalation_events"]) == 3


def test_escalation_stops_after_acknowledge(client, registrar):
    from app.core.database import SessionLocal
    from app.core.escalation import run_escalations
    from app.models.consultation import Consultation

    cid = _create(
        client, registrar, required_response_minutes=15
    ).json()["id"]
    client.post(
        f"/api/consultations/{cid}/transition",
        headers=registrar,
        json={"to_status": "acknowledged"},
    )
    db = SessionLocal()
    con = db.get(Consultation, cid)
    con.created_at = datetime.now(timezone.utc) - timedelta(minutes=200)
    db.commit()
    fired = run_escalations(db, now=datetime.now(timezone.utc))
    db.close()
    assert all(f["consultation_id"] != cid for f in fired)
