"""Outpatient appointment scheduling.

The hard no-double-book guarantee lives in the DB (a partial unique index on
station+slot over active statuses); this module computes availability, load-
balances station assignment, and books through that guarantee — catching the
integrity error and, for auto-assignment, moving to the next free station.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.scheduling import (
    Appointment,
    Clinic,
    ConsultationStation,
    SlotHold,
)
from app.models.scheduling_enums import (
    FREEING_STATUSES,
    AppointmentStatus,
    AppointmentType,
    LoadBalancing,
    StationStatus,
)

_FREEING_NAMES = [s.name for s in FREEING_STATUSES]


class SchedulingError(Exception):
    """Booking could not proceed (bad slot, off day, clinic closed)."""


class SlotUnavailable(Exception):
    """The requested station+time is already taken."""


def _parse_hm(value: str) -> tuple[int, int]:
    h, m = value.split(":")
    return int(h), int(m)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_slots(clinic: Clinic, day: date) -> list[datetime]:
    """All start times a clinic offers on `day` (empty on a non-operating day)."""
    if day.weekday() not in clinic.operating_weekdays:
        return []
    oh, om = _parse_hm(clinic.open_time)
    ch, cm = _parse_hm(clinic.close_time)
    start = datetime(day.year, day.month, day.day, oh, om)
    end = datetime(day.year, day.month, day.day, ch, cm)
    dur = timedelta(minutes=clinic.slot_duration_minutes)

    bstart = bend = None
    if clinic.break_start and clinic.break_end:
        bh, bm = _parse_hm(clinic.break_start)
        eh, em = _parse_hm(clinic.break_end)
        bstart = datetime(day.year, day.month, day.day, bh, bm)
        bend = datetime(day.year, day.month, day.day, eh, em)

    slots: list[datetime] = []
    t = start
    while t + dur <= end:
        in_break = bstart is not None and bstart <= t < bend
        if not in_break:
            slots.append(t)
        t += dur
    return slots


def active_stations(db: Session, clinic_id: int) -> list[ConsultationStation]:
    stmt = (
        select(ConsultationStation)
        .where(
            ConsultationStation.clinic_id == clinic_id,
            ConsultationStation.status == StationStatus.ACTIVE,
        )
        .order_by(ConsultationStation.station_number)
    )
    return list(db.scalars(stmt))


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day)
    return start, start + timedelta(days=1)


def _booked_map(
    db: Session, clinic_id: int, day: date
) -> dict[int, set[datetime]]:
    """station_id -> set of occupied slot_starts (active bookings)."""
    lo, hi = _day_bounds(day)
    stmt = select(
        Appointment.station_id, Appointment.slot_start
    ).where(
        Appointment.clinic_id == clinic_id,
        Appointment.slot_start >= lo,
        Appointment.slot_start < hi,
        Appointment.status.notin_(FREEING_STATUSES),
    )
    out: dict[int, set[datetime]] = {}
    for station_id, slot in db.execute(stmt):
        out.setdefault(station_id, set()).add(slot)
    return out


def _held_map(db: Session, day: date) -> dict[int, set[datetime]]:
    """station_id -> set of slot_starts under an unexpired hold."""
    lo, hi = _day_bounds(day)
    stmt = select(SlotHold.station_id, SlotHold.slot_start).where(
        SlotHold.slot_start >= lo,
        SlotHold.slot_start < hi,
        SlotHold.expires_at > _now(),
    )
    out: dict[int, set[datetime]] = {}
    for station_id, slot in db.execute(stmt):
        out.setdefault(station_id, set()).add(slot)
    return out


def station_availability(
    db: Session, clinic: Clinic, day: date
) -> list[dict]:
    """Per active station: free slots (minus booked and held) + booked count."""
    slots = generate_slots(clinic, day)
    booked = _booked_map(db, clinic.id, day)
    held = _held_map(db, day)
    result = []
    for st in active_stations(db, clinic.id):
        taken = booked.get(st.id, set()) | held.get(st.id, set())
        free = [s for s in slots if s not in taken]
        result.append(
            {
                "station": st,
                "free_slots": free,
                "booked_count": len(booked.get(st.id, set())),
            }
        )
    return result


def purge_expired_holds(db: Session) -> None:
    db.query(SlotHold).filter(SlotHold.expires_at <= _now()).delete()
    db.commit()


def _candidate_stations(
    db: Session,
    clinic: Clinic,
    slot_start: datetime,
    *,
    explicit_station_id: int | None,
) -> list[ConsultationStation]:
    """Active stations free at slot_start, ordered by load-balancing policy."""
    day = slot_start.date()
    booked = _booked_map(db, clinic.id, day)
    held = _held_map(db, day)
    stations = active_stations(db, clinic.id)

    if explicit_station_id is not None:
        stations = [s for s in stations if s.id == explicit_station_id]

    free = [
        s
        for s in stations
        if slot_start not in (booked.get(s.id, set()) | held.get(s.id, set()))
    ]
    # Least-busy first (round-robin resolves to the same even distribution via
    # the station_number tie-break).
    free.sort(key=lambda s: (len(booked.get(s.id, set())), s.station_number))
    if clinic.load_balancing == LoadBalancing.ROUND_ROBIN:
        free.sort(key=lambda s: (len(booked.get(s.id, set())), s.station_number))
    return free


def create_hold(
    db: Session,
    clinic: Clinic,
    slot_start: datetime,
    *,
    station_id: int | None,
    user_id: int | None,
) -> SlotHold:
    purge_expired_holds(db)
    if slot_start not in generate_slots(clinic, slot_start.date()):
        raise SchedulingError("That time is not an available clinic slot.")
    candidates = _candidate_stations(
        db, clinic, slot_start, explicit_station_id=station_id
    )
    if not candidates:
        raise SlotUnavailable("This appointment slot is no longer available.")
    station = candidates[0]
    hold = SlotHold(
        institution_id=clinic.institution_id,
        station_id=station.id,
        slot_start=slot_start,
        held_by_user_id=user_id,
        expires_at=_now()
        + timedelta(minutes=settings.appointment_hold_minutes),
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold


def book_appointment(
    db: Session,
    clinic: Clinic,
    *,
    patient_id: int,
    slot_start: datetime,
    appointment_type: AppointmentType,
    station_id: int | None,
    reason: str | None,
    consultation_id: int | None,
    booked_by_user_id: int | None,
) -> Appointment:
    if not clinic.is_active:
        raise SchedulingError("This clinic is not active.")
    if slot_start not in generate_slots(clinic, slot_start.date()):
        raise SchedulingError("That time is not an available clinic slot.")

    candidates = _candidate_stations(
        db, clinic, slot_start, explicit_station_id=station_id
    )
    if not candidates:
        raise SlotUnavailable("This appointment slot is no longer available.")

    # Try each candidate; the DB unique index is the real guard, so a race that
    # slips past the availability check surfaces as IntegrityError -> next one.
    last_error: IntegrityError | None = None
    for station in candidates:
        appt = Appointment(
            institution_id=clinic.institution_id,
            clinic_id=clinic.id,
            station_id=station.id,
            patient_id=patient_id,
            consultation_id=consultation_id,
            appointment_type=appointment_type,
            slot_start=slot_start,
            duration_minutes=clinic.slot_duration_minutes,
            status=AppointmentStatus.BOOKED,
            reason=reason,
            booked_by_user_id=booked_by_user_id,
        )
        db.add(appt)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
            continue
        appt.appointment_number = (
            f"APT-{clinic.id}-{slot_start:%Y%m%d}-{appt.id}"
        )
        # Release any matching hold now that the booking is durable.
        db.query(SlotHold).filter(
            SlotHold.station_id == station.id,
            SlotHold.slot_start == slot_start,
        ).delete()
        db.commit()
        db.refresh(appt)
        return appt

    if last_error is not None:
        raise SlotUnavailable("This appointment slot is no longer available.")
    raise SlotUnavailable("This appointment slot is no longer available.")


RESCHEDULABLE = {
    AppointmentStatus.BOOKED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.DID_NOT_ATTEND,
}


def reschedule_appointment(
    db: Session,
    appt: Appointment,
    clinic: Clinic,
    *,
    slot_start: datetime,
    station_id: int | None,
    booked_by_user_id: int | None,
) -> Appointment:
    """Book a replacement at the new slot, mark the old one rescheduled.

    The new booking goes through `book_appointment`, so the no-double-book
    guarantee and load balancing apply. History is preserved via
    `rescheduled_to_id`.
    """
    if appt.status not in RESCHEDULABLE:
        raise SchedulingError(
            f"Cannot reschedule an appointment that is '{appt.status.value}'."
        )
    new_appt = book_appointment(
        db,
        clinic,
        patient_id=appt.patient_id,
        slot_start=slot_start,
        appointment_type=appt.appointment_type,
        station_id=station_id,
        reason=appt.reason,
        consultation_id=appt.consultation_id,
        booked_by_user_id=booked_by_user_id,
    )
    appt.status = AppointmentStatus.RESCHEDULED
    appt.rescheduled_to_id = new_appt.id
    db.commit()
    db.refresh(new_appt)
    return new_appt


def assign_queue_position(db: Session, appt: Appointment) -> int:
    """Position among today's checked-in patients at the same station."""
    lo, hi = _day_bounds(appt.slot_start.date())
    ahead = (
        db.query(Appointment)
        .filter(
            Appointment.station_id == appt.station_id,
            Appointment.slot_start >= lo,
            Appointment.slot_start < hi,
            Appointment.checked_in_at.isnot(None),
            Appointment.id != appt.id,
        )
        .count()
    )
    return ahead + 1
