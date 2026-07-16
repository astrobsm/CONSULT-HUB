from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Patient
from app.models.scheduling import Appointment, Clinic, ConsultationStation
from app.models.scheduling_enums import (
    APPOINTMENT_TRANSITIONS,
    AppointmentStatus,
)
from app.schemas.scheduling import (
    ClinicCreate,
    ClinicUpdate,
    StationCreate,
    StationUpdate,
)
from app.services.scheduling import assign_queue_position


class InvalidAppointmentTransition(Exception):
    pass


# ---- Clinics ----

def create_clinic(
    db: Session, payload: ClinicCreate, *, institution_id: int | None
) -> Clinic:
    clinic = Clinic(**payload.model_dump(), institution_id=institution_id)
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic


def get_clinic(db: Session, clinic_id: int) -> Clinic | None:
    return db.get(Clinic, clinic_id)


def list_clinics(
    db: Session, *, institution_id: int | None
) -> list[Clinic]:
    stmt = select(Clinic).order_by(Clinic.name)
    if institution_id is not None:
        stmt = stmt.where(Clinic.institution_id == institution_id)
    return list(db.scalars(stmt))


def update_clinic(db: Session, clinic: Clinic, payload: ClinicUpdate) -> Clinic:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(clinic, field, value)
    db.commit()
    db.refresh(clinic)
    return clinic


# ---- Stations ----

def create_station(
    db: Session, clinic: Clinic, payload: StationCreate
) -> ConsultationStation:
    station = ConsultationStation(
        **payload.model_dump(),
        clinic_id=clinic.id,
        institution_id=clinic.institution_id,
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


def get_station(db: Session, station_id: int) -> ConsultationStation | None:
    return db.get(ConsultationStation, station_id)


def list_stations(db: Session, clinic_id: int) -> list[ConsultationStation]:
    stmt = (
        select(ConsultationStation)
        .where(ConsultationStation.clinic_id == clinic_id)
        .order_by(ConsultationStation.station_number)
    )
    return list(db.scalars(stmt))


def update_station(
    db: Session, station: ConsultationStation, payload: StationUpdate
) -> ConsultationStation:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(station, field, value)
    db.commit()
    db.refresh(station)
    return station


# ---- Appointments ----

def get_appointment(db: Session, appointment_id: int) -> Appointment | None:
    return db.get(Appointment, appointment_id)


def to_read(db: Session, appt: Appointment) -> dict:
    patient = db.get(Patient, appt.patient_id) if appt.patient_id else None
    station = (
        db.get(ConsultationStation, appt.station_id) if appt.station_id else None
    )
    clinic = db.get(Clinic, appt.clinic_id) if appt.clinic_id else None
    return {
        "id": appt.id,
        "appointment_number": appt.appointment_number,
        "clinic_id": appt.clinic_id,
        "clinic_name": clinic.name if clinic else None,
        "station_id": appt.station_id,
        "station_name": station.name if station else None,
        "patient_id": appt.patient_id,
        "patient_name": patient.full_name if patient else None,
        "consultation_id": appt.consultation_id,
        "appointment_type": appt.appointment_type,
        "slot_start": appt.slot_start,
        "duration_minutes": appt.duration_minutes,
        "status": appt.status,
        "queue_position": appt.queue_position,
        "reason": appt.reason,
        "rescheduled_to_id": appt.rescheduled_to_id,
        "checked_in_at": appt.checked_in_at,
        "created_at": appt.created_at,
    }


def list_appointments(
    db: Session,
    *,
    institution_id: int | None,
    clinic_id: int | None = None,
    day: date | None = None,
    status: AppointmentStatus | None = None,
    patient_id: int | None = None,
) -> list[Appointment]:
    stmt = select(Appointment).order_by(Appointment.slot_start)
    if institution_id is not None:
        stmt = stmt.where(Appointment.institution_id == institution_id)
    if clinic_id is not None:
        stmt = stmt.where(Appointment.clinic_id == clinic_id)
    if day is not None:
        lo = datetime(day.year, day.month, day.day)
        stmt = stmt.where(
            Appointment.slot_start >= lo,
            Appointment.slot_start < lo + timedelta(days=1),
        )
    if status is not None:
        stmt = stmt.where(Appointment.status == status)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    return list(db.scalars(stmt))


def transition_appointment(
    db: Session,
    appt: Appointment,
    *,
    to_status: AppointmentStatus,
    cancellation_reason: str | None = None,
) -> Appointment:
    allowed = APPOINTMENT_TRANSITIONS.get(appt.status, set())
    if to_status not in allowed:
        raise InvalidAppointmentTransition(
            f"Cannot move appointment from '{appt.status.value}' "
            f"to '{to_status.value}'."
        )
    appt.status = to_status
    if to_status == AppointmentStatus.CHECKED_IN:
        appt.checked_in_at = datetime.now().replace(microsecond=0)
        appt.queue_position = assign_queue_position(db, appt)
    if to_status == AppointmentStatus.CANCELLED:
        appt.cancellation_reason = cancellation_reason
    db.commit()
    db.refresh(appt)
    return appt
