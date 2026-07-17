from datetime import date, timedelta, timezone

MONDAY = date(2026, 7, 20).isoformat()


def _clinic(client, headers):
    return client.get("/api/clinics", headers=headers).json()[0]["id"]


def _av(client, headers, cid, day=MONDAY):
    return client.get(
        f"/api/clinics/{cid}/availability?date={day}", headers=headers
    ).json()


def _book(client, headers, cid, slot, **extra):
    body = {
        "clinic_id": cid,
        "patient_id": 1,
        "slot_start": slot,
        "appointment_type": "review",
    }
    body.update(extra)
    return client.post("/api/appointments", headers=headers, json=body).json()


def test_no_show_risk_shape_and_bands(client, registrar):
    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][0]["free_slots"][0]
    aid = _book(client, registrar, cid, slot)["id"]
    r = client.get(
        f"/api/appointments/{aid}/no-show-risk", headers=registrar
    ).json()
    assert 0.0 <= r["score"] <= 0.95
    assert r["band"] in {"low", "medium", "high"}
    assert "appointment_type" in r["factors"]


def test_wait_estimate(client, registrar):
    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][0]["free_slots"][0]
    aid = _book(client, registrar, cid, slot)["id"]
    w = client.get(
        f"/api/appointments/{aid}/wait-estimate", headers=registrar
    ).json()
    assert w["ahead_in_queue"] == 0
    assert w["slot_minutes"] == 20
    assert w["estimated_wait_minutes"] == 0


def test_reschedule_suggestions(client, registrar):
    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][0]["free_slots"][0]
    aid = _book(client, registrar, cid, slot)["id"]
    sug = client.get(
        f"/api/appointments/{aid}/suggestions", headers=registrar
    ).json()
    assert isinstance(sug, list)
    assert len(sug) <= 5
    if sug:
        assert {"slot_start", "station_id", "station_name"} <= set(sug[0])


def test_analytics_rates(client, registrar):
    cid = _clinic(client, registrar)
    av = _av(client, registrar, cid)
    slots = av["stations"][0]["free_slots"]
    a1 = _book(client, registrar, cid, slots[0])
    a2 = _book(client, registrar, cid, slots[1])
    _book(client, registrar, cid, slots[2])  # stays booked
    # complete a1, DNA a2
    for s in ["checked_in", "called", "in_progress", "completed"]:
        client.post(
            f"/api/appointments/{a1['id']}/transition",
            headers=registrar,
            json={"to_status": s},
        )
    client.post(
        f"/api/appointments/{a2['id']}/transition",
        headers=registrar,
        json={"to_status": "did_not_attend"},
    )
    an = client.get(
        f"/api/clinics/{cid}/analytics?from={MONDAY}&to={MONDAY}",
        headers=registrar,
    ).json()
    assert an["total"] == 3
    assert an["completed"] == 1
    assert an["did_not_attend"] == 1
    assert an["no_show_rate"] == 0.5  # 1 dna / (1 completed + 1 dna)
    assert an["by_type"]["review"] == 3
    assert an["peak_hours"][0]["hour"] == 8


def test_analytics_tenant_isolation(client, registrar, other_tenant):
    cid = _clinic(client, registrar)
    r = client.get(
        f"/api/clinics/{cid}/analytics?from={MONDAY}&to={MONDAY}",
        headers=other_tenant,
    )
    assert r.status_code == 404


def test_patient_email_reminder(client, registrar, monkeypatch):
    from app.core.database import SessionLocal
    from app.models.entities import Patient
    from app.models.scheduling import Appointment
    import app.services.waiting_reminders as wr

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.core.email.send_email",
        lambda to, subject, body: (sent.append((to, subject)) or True),
    )

    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][1]["free_slots"][8]
    appt = _book(client, registrar, cid, slot)

    db = SessionLocal()
    p = db.get(Patient, 1)
    p.email = "grace@example.com"
    db.commit()
    ap = db.get(Appointment, appt["id"])
    slot_dt = ap.slot_start
    if slot_dt.tzinfo is None:
        slot_dt = slot_dt.replace(tzinfo=timezone.utc)
    wr.run_reminders(db, now=slot_dt - timedelta(minutes=20))
    db.close()

    assert any(to == "grace@example.com" for to, _ in sent)
