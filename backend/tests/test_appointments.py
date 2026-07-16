from collections import Counter
from datetime import date

# 2026-07-20 is a Monday; the seeded Burn Clinic operates Mon-Fri 08:00-13:00.
MONDAY = date(2026, 7, 20).isoformat()
SUNDAY = date(2026, 7, 19).isoformat()


def _clinic_id(client, headers):
    return client.get("/api/clinics", headers=headers).json()[0]["id"]


def _availability(client, headers, cid, day=MONDAY):
    return client.get(
        f"/api/clinics/{cid}/availability?date={day}", headers=headers
    ).json()


def test_availability_generates_slots(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    # 08:00-13:00 at 20min = 15 slots per station, 3 stations
    assert len(av["stations"]) == 3
    assert all(len(s["free_slots"]) == 15 for s in av["stations"])


def test_no_double_book_same_station(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    st = av["stations"][0]["station_id"]
    slot = av["stations"][0]["free_slots"][0]
    r1 = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": slot,
            "station_id": st,
            "appointment_type": "new_patient",
        },
    )
    assert r1.status_code == 201
    assert r1.json()["appointment_number"]
    r2 = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 2,
            "slot_start": slot,
            "station_id": st,
            "appointment_type": "new_patient",
        },
    )
    assert r2.status_code == 409


def test_auto_assign_avoids_taken_station(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    st = av["stations"][0]["station_id"]
    slot = av["stations"][0]["free_slots"][0]
    a = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": slot,
            "station_id": st,
            "appointment_type": "new_patient",
        },
    ).json()
    b = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 2,
            "slot_start": slot,
            "appointment_type": "new_patient",
        },
    )
    assert b.status_code == 201
    assert b.json()["station_id"] != a["station_id"]


def test_load_distribution_even(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    slots = av["stations"][0]["free_slots"][:12]
    counts = Counter()
    for slot in slots:
        r = client.post(
            "/api/appointments",
            headers=registrar,
            json={
                "clinic_id": cid,
                "patient_id": 1,
                "slot_start": slot,
                "appointment_type": "review",
            },
        )
        counts[r.json()["station_id"]] += 1
    vals = sorted(counts.values())
    assert max(vals) - min(vals) <= 1  # even across the 3 stations
    assert vals == [4, 4, 4]


def test_off_day_rejected(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid, day=SUNDAY)
    assert sum(len(s["free_slots"]) for s in av["stations"]) == 0
    r = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": f"{SUNDAY}T08:00:00",
            "appointment_type": "review",
        },
    )
    assert r.status_code == 422


def test_lifecycle_and_queue(client, registrar):
    cid = _clinic_id(client, registrar)
    slot = _availability(client, registrar, cid)["stations"][0]["free_slots"][0]
    aid = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": slot,
            "appointment_type": "new_patient",
        },
    ).json()["id"]
    ci = client.post(
        f"/api/appointments/{aid}/transition",
        headers=registrar,
        json={"to_status": "checked_in"},
    ).json()
    assert ci["queue_position"] == 1
    for s in ["called", "in_progress", "completed"]:
        client.post(
            f"/api/appointments/{aid}/transition",
            headers=registrar,
            json={"to_status": s},
        )
    assert (
        client.get(f"/api/appointments/{aid}", headers=registrar).json()[
            "status"
        ]
        == "completed"
    )


def test_cancel_frees_slot(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    st = av["stations"][0]["station_id"]
    slot = av["stations"][0]["free_slots"][0]
    a = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": slot,
            "station_id": st,
            "appointment_type": "review",
        },
    ).json()
    client.post(
        f"/api/appointments/{a['id']}/transition",
        headers=registrar,
        json={"to_status": "cancelled", "cancellation_reason": "x"},
    )
    reb = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 2,
            "slot_start": slot,
            "station_id": st,
            "appointment_type": "review",
        },
    )
    assert reb.status_code == 201


def test_reschedule(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    st = av["stations"][0]["station_id"]
    slot_a = av["stations"][0]["free_slots"][0]
    slot_b = av["stations"][0]["free_slots"][3]
    a = client.post(
        "/api/appointments",
        headers=registrar,
        json={
            "clinic_id": cid,
            "patient_id": 1,
            "slot_start": slot_a,
            "station_id": st,
            "appointment_type": "new_patient",
        },
    ).json()
    new = client.post(
        f"/api/appointments/{a['id']}/reschedule",
        headers=registrar,
        json={"slot_start": slot_b},
    )
    assert new.status_code == 200
    assert new.json()["slot_start"].endswith("09:00:00")
    old = client.get(f"/api/appointments/{a['id']}", headers=registrar).json()
    assert old["status"] == "rescheduled"
    assert old["rescheduled_to_id"] == new.json()["id"]


def test_appointments_tenant_isolation(client, registrar, other_tenant):
    cid = _clinic_id(client, registrar)
    assert client.get("/api/clinics", headers=other_tenant).json() == []
    assert client.get(f"/api/clinics/{cid}", headers=other_tenant).status_code == 404


def test_slot_hold_removes_from_availability(client, registrar):
    cid = _clinic_id(client, registrar)
    av = _availability(client, registrar, cid)
    slot = av["stations"][1]["free_slots"][5]
    h = client.post(
        "/api/appointments/hold",
        headers=registrar,
        json={"clinic_id": cid, "slot_start": slot},
    )
    assert h.status_code == 201
    held_station = h.json()["station_id"]
    av2 = _availability(client, registrar, cid)
    station = next(s for s in av2["stations"] if s["station_id"] == held_station)
    assert slot not in station["free_slots"]
