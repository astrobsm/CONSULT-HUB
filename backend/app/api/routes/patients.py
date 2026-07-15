from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import patient as crud
from app.models.entities import Patient, User
from app.schemas.patient import PatientCreate, PatientRead

router = APIRouter(prefix="/patients", tags=["patients"])


def _get_scoped(patient_id: int, db: Session, user: User) -> Patient:
    patient = crud.get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if (
        user.institution_id is not None
        and patient.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientRead:
    return crud.create_patient(
        db, payload, institution_id=current_user.institution_id
    )


@router.get("", response_model=list[PatientRead])
def list_patients(
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PatientRead]:
    return crud.list_patients(
        db,
        institution_id=current_user.institution_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientRead:
    return _get_scoped(patient_id, db, current_user)
