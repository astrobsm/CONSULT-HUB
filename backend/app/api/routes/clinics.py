from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.crud import scheduling as crud
from app.models.entities import User
from app.models.scheduling import Clinic, ConsultationStation
from app.crud import patient as crud_patient
from app.schemas.scheduling import (
    AppointmentAnalytics,
    AvailabilityRead,
    ClinicCreate,
    ClinicRead,
    ClinicUpdate,
    StationAvailability,
    StationCreate,
    StationRead,
    StationUpdate,
    WaitingListCreate,
    WaitingListRead,
)
from app.services.analytics_appointments import appointment_analytics
from app.services.scheduling import station_availability

router = APIRouter(tags=["clinics"])


def _scoped_clinic(clinic_id: int, db: Session, user: User) -> Clinic:
    clinic = crud.get_clinic(db, clinic_id)
    if clinic is None or (
        user.institution_id is not None
        and clinic.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic


def _scoped_station(
    station_id: int, db: Session, user: User
) -> ConsultationStation:
    station = crud.get_station(db, station_id)
    if station is None or (
        user.institution_id is not None
        and station.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Station not found")
    return station


# ---- Clinics ----

@router.get("/clinics", response_model=list[ClinicRead])
def list_clinics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClinicRead]:
    return crud.list_clinics(db, institution_id=current_user.institution_id)


@router.post(
    "/clinics", response_model=ClinicRead, status_code=status.HTTP_201_CREATED
)
def create_clinic(
    payload: ClinicCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ClinicRead:
    return crud.create_clinic(
        db, payload, institution_id=admin.institution_id
    )


@router.get("/clinics/{clinic_id}", response_model=ClinicRead)
def get_clinic(
    clinic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClinicRead:
    return _scoped_clinic(clinic_id, db, current_user)


@router.patch("/clinics/{clinic_id}", response_model=ClinicRead)
def update_clinic(
    clinic_id: int,
    payload: ClinicUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ClinicRead:
    clinic = _scoped_clinic(clinic_id, db, admin)
    return crud.update_clinic(db, clinic, payload)


# ---- Stations ----

@router.get("/clinics/{clinic_id}/stations", response_model=list[StationRead])
def list_stations(
    clinic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StationRead]:
    _scoped_clinic(clinic_id, db, current_user)
    return crud.list_stations(db, clinic_id)


@router.post(
    "/clinics/{clinic_id}/stations",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_station(
    clinic_id: int,
    payload: StationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> StationRead:
    clinic = _scoped_clinic(clinic_id, db, admin)
    return crud.create_station(db, clinic, payload)


@router.patch("/stations/{station_id}", response_model=StationRead)
def update_station(
    station_id: int,
    payload: StationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> StationRead:
    station = _scoped_station(station_id, db, admin)
    return crud.update_station(db, station, payload)


# ---- Availability ----

@router.get("/clinics/{clinic_id}/availability", response_model=AvailabilityRead)
def availability(
    clinic_id: int,
    day: date = Query(alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AvailabilityRead:
    clinic = _scoped_clinic(clinic_id, db, current_user)
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


@router.get("/clinics/{clinic_id}/analytics", response_model=AppointmentAnalytics)
def clinic_analytics(
    clinic_id: int,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentAnalytics:
    clinic = _scoped_clinic(clinic_id, db, current_user)
    return appointment_analytics(
        db, clinic, date_from=date_from, date_to=date_to
    )


# ---- Waiting list ----

@router.post(
    "/clinics/{clinic_id}/waiting-list",
    response_model=WaitingListRead,
    status_code=status.HTTP_201_CREATED,
)
def join_waiting_list(
    clinic_id: int,
    payload: WaitingListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WaitingListRead:
    clinic = _scoped_clinic(clinic_id, db, current_user)
    patient = crud_patient.get_patient(db, payload.patient_id)
    if patient is None or (
        current_user.institution_id is not None
        and patient.institution_id != current_user.institution_id
    ):
        raise HTTPException(
            status_code=422, detail="Patient not found in your institution"
        )
    entry = crud.add_waiting_entry(
        db,
        clinic=clinic,
        patient_id=payload.patient_id,
        target_date=payload.target_date,
        appointment_type=payload.appointment_type,
        added_by_user_id=current_user.id,
    )
    return crud.waiting_entry_read(db, entry)


@router.get(
    "/clinics/{clinic_id}/waiting-list",
    response_model=list[WaitingListRead],
)
def list_waiting_list(
    clinic_id: int,
    day: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WaitingListRead]:
    _scoped_clinic(clinic_id, db, current_user)
    entries = crud.list_waiting_entries(db, clinic_id=clinic_id, day=day)
    return [crud.waiting_entry_read(db, e) for e in entries]


@router.delete(
    "/waiting-list/{entry_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_waiting_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    entry = crud.get_waiting_entry(db, entry_id)
    if entry is None or (
        current_user.institution_id is not None
        and entry.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
