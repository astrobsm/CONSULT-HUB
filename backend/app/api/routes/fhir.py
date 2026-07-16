from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import consultation as crud_consultation
from app.crud import patient as crud_patient
from app.fhir.mappers import (
    capability_statement,
    consultation_to_service_request,
    make_bundle,
    patient_to_fhir,
)
from app.models.entities import User

router = APIRouter(prefix="/fhir", tags=["fhir"])

FHIR_MEDIA = "application/fhir+json"


def _fhir(resource: dict[str, Any]) -> JSONResponse:
    return JSONResponse(content=resource, media_type=FHIR_MEDIA)


def _parse_reference(value: str | None) -> int | None:
    """Accept '123' or 'Patient/123' -> 123."""
    if not value:
        return None
    tail = value.rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


@router.get("/metadata")
def metadata(_: User = Depends(get_current_user)) -> JSONResponse:
    return _fhir(capability_statement())


# ---- Patient ----

@router.get("/Patient/{patient_id}")
def read_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    p = crud_patient.get_patient(db, patient_id)
    if p is None or (
        current_user.institution_id is not None
        and p.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Patient not found")
    return _fhir(patient_to_fhir(p))


@router.get("/Patient")
def search_patients(
    identifier: str | None = Query(default=None),
    name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    search = identifier or name
    patients = crud_patient.list_patients(
        db, institution_id=current_user.institution_id, search=search
    )
    return _fhir(make_bundle([patient_to_fhir(p) for p in patients]))


@router.get("/Patient/{patient_id}/$everything")
def patient_everything(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    p = crud_patient.get_patient(db, patient_id)
    if p is None or (
        current_user.institution_id is not None
        and p.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Patient not found")
    consults = crud_consultation.list_consultations(
        db, institution_id=current_user.institution_id, patient_id=patient_id
    )
    resources: list[dict[str, Any]] = [patient_to_fhir(p)]
    resources += [consultation_to_service_request(c) for c in consults]
    return _fhir(make_bundle(resources))


# ---- ServiceRequest (consultations) ----

@router.get("/ServiceRequest/{consultation_id}")
def read_service_request(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    c = crud_consultation.get_consultation(db, consultation_id)
    if c is None or (
        current_user.institution_id is not None
        and c.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=404, detail="ServiceRequest not found")
    return _fhir(consultation_to_service_request(c))


@router.get("/ServiceRequest")
def search_service_requests(
    patient: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    consults = crud_consultation.list_consultations(
        db,
        institution_id=current_user.institution_id,
        patient_id=_parse_reference(patient),
    )
    return _fhir(
        make_bundle([consultation_to_service_request(c) for c in consults])
    )
