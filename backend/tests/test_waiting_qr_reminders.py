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
    return client.post("/api/appointments", headers=headers, json=body)


# ---- QR check-in ----

def test_booking_has_check_in_code_and_qr(client, registrar):
    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][0]["free_slots"][0]
    appt = _book(client, registrar, cid, slot).json()
    assert appt["check_in_code"]
    qr = client.get(
        f"/api/appointments/{appt['id']}/qrcode", headers=registrar
    )
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/svg+xml"
    assert "<svg" in qr.text


def test_check_in_by_code(client, registrar):
    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][0]["free_slots"][0]
    appt = _book(client, registrar, cid, slot).json()
    r = client.post(
        "/api/appointments/check-in",
        headers=registrar,
        json={"code": appt["check_in_code"]},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "checked_in"
    assert r.json()["queue_position"] == 1


def test_check_in_bad_code(client, registrar):
    r = client.post(
        "/api/appointments/check-in",
        headers=registrar,
        json={"code": "does-not-exist"},
    )
    assert r.status_code == 404


def test_check_in_tenant_isolation(client, registrar, other_tenant):
    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][0]["free_slots"][0]
    appt = _book(client, registrar, cid, slot).json()
    # other tenant can't check in with our code (looks like a bad code -> 404)
    r = client.post(
        "/api/appointments/check-in",
        headers=other_tenant,
        json={"code": appt["check_in_code"]},
    )
    assert r.status_code == 404


# ---- Waiting list + auto-promotion ----

def test_waiting_list_auto_promote_on_cancel(client, registrar):
    cid = _clinic(client, registrar)
    av = _av(client, registrar, cid)
    slot = av["stations"][0]["free_slots"][0]
    # fill the slot on every station
    booked = []
    for stn in av["stations"]:
        r = _book(
            client, registrar, cid, slot, station_id=stn["station_id"]
        )
        if r.status_code == 201:
            booked.append(r.json()["id"])
    assert booked
    # patient 2 joins the waiting list
    w = client.post(
        f"/api/clinics/{cid}/waiting-list",
        headers=registrar,
        json={
            "patient_id": 2,
            "target_date": f"{MONDAY}T00:00:00",
            "appointment_type": "review",
        },
    )
    assert w.status_code == 201
    assert w.json()["status"] == "waiting"
    # cancel one -> auto-promote
    client.post(
        f"/api/appointments/{booked[0]}/transition",
        headers=registrar,
        json={"to_status": "cancelled", "cancellation_reason": "x"},
    )
    entries = client.get(
        f"/api/clinics/{cid}/waiting-list?date={MONDAY}", headers=registrar
    ).json()
    promoted = [e for e in entries if e["status"] == "promoted"]
    assert len(promoted) == 1
    assert promoted[0]["promoted_appointment_id"] is not None


def test_waiting_list_tenant_isolation(client, registrar, other_tenant):
    cid = _clinic(client, registrar)
    assert (
        client.get(
            f"/api/clinics/{cid}/waiting-list", headers=other_tenant
        ).status_code
        == 404
    )


# ---- Reminders ----

def test_reminders_fire_tightest_only_and_idempotent(client, registrar):
    from app.core.database import SessionLocal
    from app.models.scheduling import Appointment
    from app.services.waiting_reminders import run_reminders

    cid = _clinic(client, registrar)
    slot = _av(client, registrar, cid)["stations"][1]["free_slots"][8]
    appt = _book(client, registrar, cid, slot).json()
    aid = appt["id"]

    db = SessionLocal()
    ap = db.get(Appointment, aid)
    slot_dt = ap.slot_start
    if slot_dt.tzinfo is None:
        slot_dt = slot_dt.replace(tzinfo=timezone.utc)

    now = slot_dt - timedelta(minutes=20)  # crosses 30m (and larger)
    fired = run_reminders(db, now=now)
    ours = [f["offset"] for f in fired if f["appointment_id"] == aid]
    assert ours == ["30m"]  # tightest only
    # idempotent: same now -> nothing new for our appt
    fired2 = run_reminders(db, now=now)
    assert all(f["appointment_id"] != aid for f in fired2)
    db.close()

    rem = [
        n
        for n in client.get("/api/notifications", headers=registrar).json()
        if n["kind"] == "reminder"
    ]
    assert len(rem) >= 1
    assert "30m" in rem[0]["title"]
