from datetime import date, timedelta, timezone

MONDAY = date(2026, 7, 20).isoformat()


def test_console_sms_is_best_effort(client):
    # No Twilio configured -> send_sms logs and returns True.
    from app.core.sms import send_sms, send_whatsapp

    assert send_sms("+2348000000000", "hello") is True
    assert send_whatsapp("+2348000000000", "hi") is True
    assert send_sms(None, "x") is False


def test_patient_sms_reminder(client, registrar, monkeypatch):
    from app.core.database import SessionLocal
    from app.models.entities import Patient
    from app.models.scheduling import Appointment
    import app.services.waiting_reminders as wr

    sms: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.core.sms.send_sms",
        lambda to, body: (sms.append((to, body)) or True),
    )

    cid = client.get("/api/clinics", headers=registrar).json()[0]["id"]
    slot = client.get(
        f"/api/clinics/{cid}/availability?date={MONDAY}", headers=registrar
    ).json()["stations"][0]["free_slots"][0]
    appt = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": slot,
            "appointment_type": "review",
        },
    ).json()

    db = SessionLocal()
    p = db.get(Patient, 1)
    p.phone = "+2348001234567"
    db.commit()
    ap = db.get(Appointment, appt["id"])
    slot_dt = ap.slot_start
    if slot_dt.tzinfo is None:
        slot_dt = slot_dt.replace(tzinfo=timezone.utc)
    wr.run_reminders(db, now=slot_dt - timedelta(minutes=20))
    db.close()

    assert any(to == "+2348001234567" for to, _ in sms)
