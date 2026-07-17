from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import patient as crud_patient
from app.crud import scheduling as crud
from app.crud.scheduling import InvalidAppointmentTransition
from app.models.entities import User
from app.models.scheduling import Appointment
from app.models.scheduling_enums import AppointmentStatus
from app.schemas.scheduling import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentTransition,
    CheckInRequest,
    HoldCreate,
    HoldRead,
    NoShowRisk,
    RescheduleRequest,
    SlotSuggestion,
    WaitEstimate,
)
from app.services import intelligence
from app.services.notifications import notify_appointment
from app.services.qr import generate_qr_svg
from app.services.scheduling import (
    SchedulingError,
    SlotUnavailable,
    book_appointment,
    create_hold,
    reschedule_appointment,
)
from app.services.waiting_reminders import promote_from_waiting_list

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _scoped_clinic(clinic_id: int, db: Session, user: User):
    clinic = crud.get_clinic(db, clinic_id)
    if clinic is None or (
        user.institution_id is not None
        and clinic.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic


def _scoped_appointment(
    appointment_id: int, db: Session, user: User
) -> Appointment:
    appt = crud.get_appointment(db, appointment_id)
    if appt is None or (
        user.institution_id is not None
        and appt.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.post("/hold", response_model=HoldRead, status_code=201)
def hold_slot(
    payload: HoldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HoldRead:
    clinic = _scoped_clinic(payload.clinic_id, db, current_user)
    try:
        return create_hold(
            db,
            clinic,
            payload.slot_start,
            station_id=payload.station_id,
            user_id=current_user.id,
        )
    except SlotUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED
)
def book(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    clinic = _scoped_clinic(payload.clinic_id, db, current_user)

    patient = crud_patient.get_patient(db, payload.patient_id)
    if patient is None or (
        current_user.institution_id is not None
        and patient.institution_id != current_user.institution_id
    ):
        raise HTTPException(
            status_code=422, detail="Patient not found in your institution"
        )

    try:
        appt = book_appointment(
            db,
            clinic,
            patient_id=payload.patient_id,
            slot_start=payload.slot_start,
            appointment_type=payload.appointment_type,
            station_id=payload.station_id,
            reason=payload.reason,
            consultation_id=payload.consultation_id,
            booked_by_user_id=current_user.id,
        )
    except SlotUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    station = crud.get_station(db, appt.station_id)
    notify_appointment(
        db,
        institution_id=appt.institution_id,
        assigned_user_id=station.assigned_user_id if station else None,
        clinic_name=clinic.name,
        patient_name=patient.full_name,
        slot_start=appt.slot_start.strftime("%Y-%m-%d %H:%M"),
        event="booked",
    )
    return crud.to_read(db, appt)


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    clinic_id: int | None = Query(default=None),
    day: date | None = Query(default=None, alias="date"),
    status_filter: AppointmentStatus | None = Query(
        default=None, alias="status"
    ),
    patient_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AppointmentRead]:
    appts = crud.list_appointments(
        db,
        institution_id=current_user.institution_id,
        clinic_id=clinic_id,
        day=day,
        status=status_filter,
        patient_id=patient_id,
    )
    return [crud.to_read(db, a) for a in appts]


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    appt = _scoped_appointment(appointment_id, db, current_user)
    return crud.to_read(db, appt)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule(
    appointment_id: int,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    appt = _scoped_appointment(appointment_id, db, current_user)
    clinic = _scoped_clinic(appt.clinic_id, db, current_user)
    try:
        new_appt = reschedule_appointment(
            db,
            appt,
            clinic,
            slot_start=payload.slot_start,
            station_id=payload.station_id,
            booked_by_user_id=current_user.id,
        )
    except SlotUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    station = crud.get_station(db, new_appt.station_id)
    patient = crud_patient.get_patient(db, new_appt.patient_id)
    notify_appointment(
        db,
        institution_id=new_appt.institution_id,
        assigned_user_id=station.assigned_user_id if station else None,
        clinic_name=clinic.name,
        patient_name=patient.full_name if patient else "Patient",
        slot_start=new_appt.slot_start.strftime("%Y-%m-%d %H:%M"),
        event="rescheduled",
    )
    return crud.to_read(db, new_appt)


@router.post("/{appointment_id}/transition", response_model=AppointmentRead)
def transition(
    appointment_id: int,
    payload: AppointmentTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    appt = _scoped_appointment(appointment_id, db, current_user)
    try:
        updated = crud.transition_appointment(
            db,
            appt,
            to_status=payload.to_status,
            cancellation_reason=payload.cancellation_reason,
        )
    except InvalidAppointmentTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if payload.to_status == AppointmentStatus.CANCELLED:
        station = crud.get_station(db, updated.station_id)
        patient = crud_patient.get_patient(db, updated.patient_id)
        clinic = crud.get_clinic(db, updated.clinic_id)
        notify_appointment(
            db,
            institution_id=updated.institution_id,
            assigned_user_id=station.assigned_user_id if station else None,
            clinic_name=clinic.name if clinic else "Clinic",
            patient_name=patient.full_name if patient else "Patient",
            slot_start=updated.slot_start.strftime("%Y-%m-%d %H:%M"),
            event="cancelled",
        )
        # A slot just freed — promote the next waiting patient, if any.
        if clinic is not None:
            promote_from_waiting_list(db, clinic, updated.slot_start.date())
    return crud.to_read(db, updated)


@router.post("/check-in", response_model=AppointmentRead)
def check_in(
    payload: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    """Reception check-in by scanning/entering the QR code."""
    appt = crud.get_appointment_by_code(db, payload.code.strip())
    if appt is None or (
        current_user.institution_id is not None
        and appt.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        updated = crud.transition_appointment(
            db, appt, to_status=AppointmentStatus.CHECKED_IN
        )
    except InvalidAppointmentTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return crud.to_read(db, updated)


@router.get("/{appointment_id}/no-show-risk", response_model=NoShowRisk)
def no_show_risk(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoShowRisk:
    appt = _scoped_appointment(appointment_id, db, current_user)
    return intelligence.no_show_risk(db, appt)


@router.get("/{appointment_id}/wait-estimate", response_model=WaitEstimate)
def wait_estimate(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WaitEstimate:
    appt = _scoped_appointment(appointment_id, db, current_user)
    return intelligence.wait_estimate(db, appt)


@router.get(
    "/{appointment_id}/suggestions", response_model=list[SlotSuggestion]
)
def reschedule_suggestions(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SlotSuggestion]:
    appt = _scoped_appointment(appointment_id, db, current_user)
    return intelligence.reschedule_suggestions(db, appt)


@router.get("/{appointment_id}/qrcode")
def appointment_qrcode(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    appt = _scoped_appointment(appointment_id, db, current_user)
    if not appt.check_in_code:
        raise HTTPException(status_code=404, detail="No check-in code")
    svg = generate_qr_svg(appt.check_in_code)
    return Response(content=svg, media_type="image/svg+xml")
