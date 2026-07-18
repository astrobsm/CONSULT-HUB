"""Patient self-service portal.

A separate authentication surface: patients activate an account (via an emailed
link), log in for a patient-scoped JWT (typ="patient"), and can only ever see and
act on their own data within their own institution. Patient tokens are rejected
by staff endpoints and vice-versa (see app/api/deps.py).
"""

from __future__ import annotations

from datetime import date

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import (
    create_access_token,
    create_purpose_token,
    decode_purpose_token,
    hash_password,
)
from app.crud import patient as crud_patient
from app.crud import scheduling as crud
from app.crud.scheduling import InvalidAppointmentTransition
from app.models.entities import Patient
from app.models.scheduling import Appointment, Clinic
from app.models.scheduling_enums import AppointmentStatus
from app.schemas.scheduling import (
    AppointmentRead,
    AvailabilityRead,
    ClinicRead,
    StationAvailability,
)
from app.schemas.portal import (
    PatientPortalRead,
    PortalActivateRequest,
    PortalBook,
    PortalReschedule,
    PortalSetPassword,
    PortalToken,
    PortalWaitingList,
)
from app.services.scheduling import (
    SchedulingError,
    SlotUnavailable,
    book_appointment,
    reschedule_appointment,
    station_availability,
)
from app.services.waiting_reminders import promote_from_waiting_list

router = APIRouter(prefix="/portal", tags=["portal"])


# ---- Activation & auth ----

@router.post("/activate", status_code=status.HTTP_202_ACCEPTED)
def activate(
    payload: PortalActivateRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    # Always 202 — never reveal whether a record matched.
    patient = crud_patient.find_for_activation(
        db,
        hospital_number=payload.hospital_number.strip(),
        email=payload.email.strip().lower(),
    )
    if patient is not None and patient.email:
        token = create_purpose_token(
            patient.id, "portal", settings.invite_token_expire_minutes
        )
        link = f"{settings.frontend_base_url}/portal/set-password?token={token}"
        send_email(
            patient.email,
            "Activate your ConsultHUB patient portal",
            "Set a password to access your appointments:\n\n"
            f"{link}\n\nIf you didn't request this, ignore this email.",
        )
    return {"status": "accepted"}


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(
    payload: PortalSetPassword, db: Session = Depends(get_db)
) -> None:
    try:
        patient_id = decode_purpose_token(payload.token, {"portal"})
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=400, detail="Invalid or expired token"
        )
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=400, detail="Invalid or expired token"
        )
    patient.hashed_password = hash_password(payload.password)
    db.commit()


@router.post("/login", response_model=PortalToken)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> PortalToken:
    patient = crud_patient.authenticate_patient(
        db, form_data.username, form_data.password
    )
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        patient.id, extra={"typ": "patient", "inst": patient.institution_id}
    )
    return PortalToken(
        access_token=token, patient=PatientPortalRead.model_validate(patient)
    )


@router.get("/me", response_model=PatientPortalRead)
def me(patient: Patient = Depends(get_current_patient)) -> PatientPortalRead:
    return patient


# ---- Clinics & availability (patient's institution only) ----

def _scoped_clinic(clinic_id: int, db: Session, patient: Patient) -> Clinic:
    clinic = crud.get_clinic(db, clinic_id)
    if (
        clinic is None
        or not clinic.is_active
        or clinic.institution_id != patient.institution_id
    ):
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic


@router.get("/clinics", response_model=list[ClinicRead])
def list_clinics(
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> list[ClinicRead]:
    return [
        c
        for c in crud.list_clinics(db, institution_id=patient.institution_id)
        if c.is_active
    ]


@router.get(
    "/clinics/{clinic_id}/availability", response_model=AvailabilityRead
)
def availability(
    clinic_id: int,
    day: date = Query(alias="date"),
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> AvailabilityRead:
    clinic = _scoped_clinic(clinic_id, db, patient)
    rows = station_availability(db, clinic, day)
    return AvailabilityRead(
        clinic_id=clinic.id,
        date=day.isoformat(),
        slot_duration_minutes=clinic.slot_duration_minutes,
        stations=[
            StationAvailability(
                station_id=r["station"].id,
                station_name=r["station"].name,
                booked_count=r["booked_count"],
                free_slots=r["free_slots"],
            )
            for r in rows
        ],
    )


# ---- Appointments (self only) ----

def _own_appointment(
    appointment_id: int, db: Session, patient: Patient
) -> Appointment:
    appt = crud.get_appointment(db, appointment_id)
    if appt is None or appt.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.get("/appointments", response_model=list[AppointmentRead])
def my_appointments(
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> list[AppointmentRead]:
    appts = db.scalars(
        select(Appointment)
        .where(Appointment.patient_id == patient.id)
        .order_by(Appointment.slot_start.desc())
    )
    return [crud.to_read(db, a) for a in appts]


@router.post(
    "/appointments",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
)
def self_book(
    payload: PortalBook,
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> AppointmentRead:
    clinic = _scoped_clinic(payload.clinic_id, db, patient)
    try:
        appt = book_appointment(
            db,
            clinic,
            patient_id=patient.id,
            slot_start=payload.slot_start,
            appointment_type=payload.appointment_type,
            station_id=payload.station_id,
            reason="Booked by patient (portal)",
            consultation_id=None,
            booked_by_user_id=None,
        )
    except SlotUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Confirmation to the patient's phone, if we have one.
    if patient.phone:
        from app.core.sms import send_sms

        send_sms(
            patient.phone,
            f"ConsultHUB: appointment {appt.appointment_number} confirmed for "
            f"{appt.slot_start.strftime('%Y-%m-%d %H:%M')}.",
        )
    return crud.to_read(db, appt)


@router.post(
    "/appointments/{appointment_id}/cancel", response_model=AppointmentRead
)
def cancel(
    appointment_id: int,
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> AppointmentRead:
    appt = _own_appointment(appointment_id, db, patient)
    try:
        updated = crud.transition_appointment(
            db,
            appt,
            to_status=AppointmentStatus.CANCELLED,
            cancellation_reason="Cancelled by patient (portal)",
        )
    except InvalidAppointmentTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    clinic = crud.get_clinic(db, updated.clinic_id)
    if clinic is not None:
        promote_from_waiting_list(db, clinic, updated.slot_start.date())
    return crud.to_read(db, updated)


@router.post(
    "/appointments/{appointment_id}/reschedule",
    response_model=AppointmentRead,
)
def reschedule(
    appointment_id: int,
    payload: PortalReschedule,
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> AppointmentRead:
    appt = _own_appointment(appointment_id, db, patient)
    clinic = _scoped_clinic(appt.clinic_id, db, patient)
    try:
        new_appt = reschedule_appointment(
            db,
            appt,
            clinic,
            slot_start=payload.slot_start,
            station_id=payload.station_id,
            booked_by_user_id=None,
        )
    except SlotUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return crud.to_read(db, new_appt)


@router.post("/waiting-list", status_code=status.HTTP_201_CREATED)
def join_waiting_list(
    payload: PortalWaitingList,
    db: Session = Depends(get_db),
    patient: Patient = Depends(get_current_patient),
) -> dict[str, str]:
    clinic = _scoped_clinic(payload.clinic_id, db, patient)
    crud.add_waiting_entry(
        db,
        clinic=clinic,
        patient_id=patient.id,
        target_date=payload.target_date,
        appointment_type=payload.appointment_type,
        added_by_user_id=None,
    )
    return {"status": "added"}
