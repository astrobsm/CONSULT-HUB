"""Appointment intelligence — transparent, data-driven estimators.

These are **heuristics**, not machine learning: each returns a score plus the
factors that produced it, so the output is explainable. They form a clean
extension point where a trained model / LLM can be dropped in later without
changing the API surface.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduling import Appointment, Clinic, ConsultationStation
from app.models.scheduling_enums import AppointmentStatus, AppointmentType

# Statuses that mean the patient turned up.
_ATTENDED = {
    AppointmentStatus.CHECKED_IN,
    AppointmentStatus.WAITING,
    AppointmentStatus.CALLED,
    AppointmentStatus.IN_PROGRESS,
    AppointmentStatus.COMPLETED,
    AppointmentStatus.REFERRED,
    AppointmentStatus.ADMITTED,
    AppointmentStatus.DISCHARGED,
}
_ACTIVE_IN_CLINIC = {
    AppointmentStatus.CHECKED_IN,
    AppointmentStatus.WAITING,
    AppointmentStatus.CALLED,
    AppointmentStatus.IN_PROGRESS,
}

_BASE_NO_SHOW = 0.15
# Urgent/emergency patients rarely miss; routine reviews miss more.
_TYPE_FACTOR = {
    AppointmentType.EMERGENCY: 0.3,
    AppointmentType.WALK_IN: 0.3,
    AppointmentType.PRIORITY: 0.6,
    AppointmentType.POSTOPERATIVE: 0.7,
    AppointmentType.PROCEDURE: 0.7,
    AppointmentType.NEW_PATIENT: 1.1,
    AppointmentType.REVIEW: 1.2,
    AppointmentType.FOLLOW_UP: 1.2,
}


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def no_show_risk(db: Session, appt: Appointment) -> dict:
    history = list(
        db.scalars(
            select(Appointment).where(
                Appointment.patient_id == appt.patient_id,
                Appointment.id != appt.id,
            )
        )
    )
    dna = sum(
        1 for a in history if a.status == AppointmentStatus.DID_NOT_ATTEND
    )
    attended = sum(1 for a in history if a.status in _ATTENDED)
    decided = dna + attended

    if decided >= 3:
        base = dna / decided
        basis = "patient history"
    else:
        base = _BASE_NO_SHOW
        basis = "population base rate (little history)"

    type_factor = _TYPE_FACTOR.get(appt.appointment_type, 1.0)

    lead_days = max(
        0, (_as_utc(appt.slot_start) - _as_utc(appt.created_at)).days
    )
    lead_factor = 1.0 + min(lead_days, 30) * 0.01  # up to +30%

    score = max(0.0, min(0.95, base * type_factor * lead_factor))
    band = "high" if score >= 0.35 else "medium" if score >= 0.15 else "low"

    return {
        "score": round(score, 3),
        "band": band,
        "factors": {
            "basis": basis,
            "past_attended": attended,
            "past_no_shows": dna,
            "lead_days": lead_days,
            "appointment_type": appt.appointment_type.value,
        },
    }


def wait_estimate(db: Session, appt: Appointment) -> dict:
    clinic = db.get(Clinic, appt.clinic_id)
    slot_minutes = clinic.slot_duration_minutes if clinic else 20

    day = appt.slot_start.date()
    lo = datetime(day.year, day.month, day.day)
    hi = lo + timedelta(days=1)
    ahead = (
        db.query(Appointment)
        .filter(
            Appointment.station_id == appt.station_id,
            Appointment.slot_start >= lo,
            Appointment.slot_start < hi,
            Appointment.slot_start <= appt.slot_start,
            Appointment.id != appt.id,
            Appointment.status.in_(_ACTIVE_IN_CLINIC),
        )
        .count()
    )
    return {
        "estimated_wait_minutes": ahead * slot_minutes,
        "ahead_in_queue": ahead,
        "slot_minutes": slot_minutes,
    }


def reschedule_suggestions(
    db: Session,
    appt: Appointment,
    *,
    days: int = 14,
    limit: int = 5,
    from_date: date | None = None,
) -> list[dict]:
    """Earliest free slots across the clinic over the coming days."""
    from app.services.scheduling import station_availability

    clinic = db.get(Clinic, appt.clinic_id)
    if clinic is None:
        return []
    start = from_date or date.today()

    found: list[dict] = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        for row in station_availability(db, clinic, d):
            station: ConsultationStation = row["station"]
            for slot in row["free_slots"]:
                if slot == appt.slot_start:
                    continue
                found.append(
                    {
                        "slot_start": slot,
                        "station_id": station.id,
                        "station_name": station.name,
                    }
                )
    found.sort(key=lambda s: s["slot_start"])
    return found[:limit]
