from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.crud import scheduling as crud
from app.models.entities import User
from app.models.scheduling import Clinic, ConsultationStation
from app.schemas.scheduling import (
    AvailabilityRead,
    ClinicCreate,
    ClinicRead,
    ClinicUpdate,
    StationAvailability,
    StationCreate,
    StationRead,
    StationUpdate,
)
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
