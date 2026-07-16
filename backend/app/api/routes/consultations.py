from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import consultation as crud
from app.crud import patient as crud_patient
from app.crud.consultation import InvalidTransition
from app.models.consultation import Consultation
from app.models.entities import User
from app.models.enums import ConsultationStatus
from app.services.notifications import notify_status_change
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationRead,
    ConsultationTransition,
)

router = APIRouter(prefix="/consultations", tags=["consultations"])


def _get_scoped(
    consultation_id: int, db: Session, user: User
) -> Consultation:
    """Fetch a consultation, enforcing the caller's tenant boundary."""
    consultation = crud.get_consultation(db, consultation_id)
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if (
        user.institution_id is not None
        and consultation.institution_id != user.institution_id
    ):
        # Do not leak existence across tenants.
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultation


@router.post(
    "", response_model=ConsultationRead, status_code=status.HTTP_201_CREATED
)
def create_consultation(
    payload: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsultationRead:
    if payload.patient_id is not None:
        patient = crud_patient.get_patient(db, payload.patient_id)
        same_tenant = patient is not None and (
            current_user.institution_id is None
            or patient.institution_id == current_user.institution_id
        )
        if not same_tenant:
            raise HTTPException(
                status_code=422, detail="Patient not found in your institution"
            )
    return crud.create_consultation(
        db,
        payload,
        requesting_user_id=current_user.id,
        institution_id=current_user.institution_id,
    )


@router.get("", response_model=list[ConsultationRead])
def list_consultations(
    status_filter: ConsultationStatus | None = Query(
        default=None, alias="status"
    ),
    patient_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConsultationRead]:
    return crud.list_consultations(
        db,
        institution_id=current_user.institution_id,
        patient_id=patient_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/{consultation_id}", response_model=ConsultationRead)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsultationRead:
    return _get_scoped(consultation_id, db, current_user)


@router.post("/{consultation_id}/transition", response_model=ConsultationRead)
def transition_consultation(
    consultation_id: int,
    payload: ConsultationTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsultationRead:
    consultation = _get_scoped(consultation_id, db, current_user)
    try:
        updated = crud.transition_consultation(
            db,
            consultation,
            to_status=payload.to_status,
            actor_user_id=current_user.id,
            note=payload.note,
        )
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    notify_status_change(
        db,
        updated,
        to_status=payload.to_status,
        actor_user_id=current_user.id,
    )
    return updated
