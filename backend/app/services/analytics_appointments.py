"""Clinic appointment analytics over a date range."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduling import Appointment, Clinic, ConsultationStation
from app.models.scheduling_enums import AppointmentStatus


def _range_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    lo = datetime(date_from.year, date_from.month, date_from.day)
    hi = datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1)
    return lo, hi


def appointment_analytics(
    db: Session,
    clinic: Clinic,
    *,
    date_from: date,
    date_to: date,
) -> dict:
    lo, hi = _range_bounds(date_from, date_to)
    appts = list(
        db.scalars(
            select(Appointment).where(
                Appointment.clinic_id == clinic.id,
                Appointment.slot_start >= lo,
                Appointment.slot_start < hi,
            )
        )
    )

    total = len(appts)
    by_status: Counter[str] = Counter(a.status.value for a in appts)
    completed = by_status.get(AppointmentStatus.COMPLETED.value, 0)
    dna = by_status.get(AppointmentStatus.DID_NOT_ATTEND.value, 0)
    cancelled = by_status.get(AppointmentStatus.CANCELLED.value, 0)

    # No-show rate is over appointments that actually resolved (attended or not).
    resolved = completed + dna
    no_show_rate = round(dna / resolved, 3) if resolved else 0.0
    completion_rate = round(completed / total, 3) if total else 0.0
    cancellation_rate = round(cancelled / total, 3) if total else 0.0

    by_type: Counter[str] = Counter(a.appointment_type.value for a in appts)
    by_hour: Counter[int] = Counter(a.slot_start.hour for a in appts)

    # Per-station load (productivity) with names.
    station_names = {
        s.id: s.name
        for s in db.scalars(
            select(ConsultationStation).where(
                ConsultationStation.clinic_id == clinic.id
            )
        )
    }
    by_station_id: Counter[int] = Counter(a.station_id for a in appts)
    by_station = [
        {
            "station_id": sid,
            "station_name": station_names.get(sid, f"Station {sid}"),
            "count": count,
        }
        for sid, count in by_station_id.most_common()
    ]

    peak_hours = [
        {"hour": h, "count": c} for h, c in sorted(by_hour.items())
    ]

    return {
        "clinic_id": clinic.id,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total": total,
        "completed": completed,
        "did_not_attend": dna,
        "cancelled": cancelled,
        "no_show_rate": no_show_rate,
        "completion_rate": completion_rate,
        "cancellation_rate": cancellation_rate,
        "by_status": dict(by_status),
        "by_type": dict(by_type),
        "peak_hours": peak_hours,
        "by_station": by_station,
    }
