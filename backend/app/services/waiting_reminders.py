"""Waiting list auto-promotion and appointment reminders.

Both are pure functions of the DB (+ an injectable `now` for reminders), so they
are deterministically testable. The reminder engine runs on the shared scheduler.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduling import (
    Appointment,
    AppointmentReminder,
    Clinic,
    ConsultationStation,
    WaitingListEntry,
)
from app.models.scheduling_enums import (
    REMINDER_OFFSETS,
    AppointmentStatus,
    WaitingStatus,
)
from app.services.scheduling import SlotUnavailable, book_appointment

logger = logging.getLogger("consulthub.waiting_reminders")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- Waiting list ----

def promote_from_waiting_list(
    db: Session, clinic: Clinic, day: date
) -> Appointment | None:
    """Book the oldest waiting patient into an available slot on `day`.

    Called when a slot frees (e.g. a cancellation). Returns the new appointment
    or None if nobody is waiting / no slot could be booked.
    """
    lo = datetime(day.year, day.month, day.day)
    hi = lo + timedelta(days=1)
    stmt = (
        select(WaitingListEntry)
        .where(
            WaitingListEntry.clinic_id == clinic.id,
            WaitingListEntry.status == WaitingStatus.WAITING,
            WaitingListEntry.target_date >= lo,
            WaitingListEntry.target_date < hi,
        )
        .order_by(WaitingListEntry.created_at)
    )
    from app.services.scheduling import generate_slots, station_availability

    slots = generate_slots(clinic, day)
    if not slots:
        return None

    for entry in db.scalars(stmt):
        # First free slot across any active station.
        avail = station_availability(db, clinic, day)
        free = sorted({s for row in avail for s in row["free_slots"]})
        if not free:
            return None
        try:
            appt = book_appointment(
                db,
                clinic,
                patient_id=entry.patient_id,
                slot_start=free[0],
                appointment_type=entry.appointment_type,
                station_id=None,
                reason="Promoted from waiting list",
                consultation_id=None,
                booked_by_user_id=entry.added_by_user_id,
            )
        except SlotUnavailable:
            continue
        entry.status = WaitingStatus.PROMOTED
        entry.promoted_appointment_id = appt.id
        db.commit()
        db.refresh(appt)
        return appt
    return None


# ---- Reminders ----

def _reminder_recipients(
    db: Session, appt: Appointment
) -> set[int]:
    recipients: set[int] = set()
    if appt.booked_by_user_id:
        recipients.add(appt.booked_by_user_id)
    station = db.get(ConsultationStation, appt.station_id)
    if station and station.assigned_user_id:
        recipients.add(station.assigned_user_id)
    return recipients


def run_reminders(db: Session, now: datetime | None = None) -> list[dict]:
    """Send reminders for upcoming appointments crossing a reminder offset.

    Each offset fires once. On catch-up, only the tightest crossed-but-unsent
    offset notifies; looser ones are marked sent silently to avoid a burst.
    """
    now = now or _now()
    from app.crud import notification as crud_notification
    from app.core.config import settings
    from app.core.email import send_email
    from app.core.sms import send_sms, send_whatsapp
    from app.models.entities import Patient

    stmt = select(Appointment).where(
        Appointment.status.in_(
            [AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED]
        ),
        Appointment.slot_start > now,
    )
    fired: list[dict] = []
    for appt in db.scalars(stmt):
        slot = appt.slot_start
        if slot.tzinfo is None:
            slot = slot.replace(tzinfo=timezone.utc)

        sent = {
            r.offset_label
            for r in db.scalars(
                select(AppointmentReminder).where(
                    AppointmentReminder.appointment_id == appt.id
                )
            )
        }
        crossed = [
            (minutes, label)
            for minutes, label in REMINDER_OFFSETS
            if label not in sent and now >= slot - timedelta(minutes=minutes)
        ]
        if not crossed:
            continue
        tightest = min(crossed, key=lambda x: x[0])
        for _, label in crossed:
            db.add(
                AppointmentReminder(
                    appointment_id=appt.id,
                    institution_id=appt.institution_id,
                    offset_label=label,
                    sent_at=now,
                )
            )
        # Notify staff in-app for the tightest bucket.
        when = slot.strftime("%Y-%m-%d %H:%M")
        for user_id in _reminder_recipients(db, appt):
            crud_notification.create_notification(
                db,
                user_id=user_id,
                institution_id=appt.institution_id,
                kind="reminder",
                title=f"Reminder: appointment in {tightest[1]}",
                body=(
                    f"Appointment {appt.appointment_number or appt.id} "
                    f"is scheduled for {when}."
                ),
            )
        # Patient-facing reminders across whatever channels we can reach.
        patient = db.get(Patient, appt.patient_id)
        if patient:
            ref = appt.appointment_number or appt.id
            if patient.email:
                send_email(
                    patient.email,
                    f"Appointment reminder — {when}",
                    f"Dear {patient.full_name}, this is a reminder that you "
                    f"have an appointment on {when} (ref {ref}). "
                    "Please arrive 10 minutes early to check in.",
                )
            if patient.phone:
                sms = (
                    f"ConsultHUB: reminder — appointment {when} "
                    f"(ref {ref}). Please arrive 10 min early."
                )
                send_sms(patient.phone, sms)
                if settings.whatsapp_enabled:
                    send_whatsapp(patient.phone, sms)
        fired.append({"appointment_id": appt.id, "offset": tightest[1]})

    if fired:
        db.commit()
    return fired


def run_reminders_job() -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        fired = run_reminders(db)
        if fired:
            logger.info("Reminders sent: %d", len(fired))
    except Exception:
        logger.exception("Reminder run failed")
    finally:
        db.close()
