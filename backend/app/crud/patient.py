from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import Patient
from app.schemas.patient import PatientCreate


def create_patient(
    db: Session, payload: PatientCreate, *, institution_id: int | None
) -> Patient:
    patient = Patient(**payload.model_dump(), institution_id=institution_id)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patient(db: Session, patient_id: int) -> Patient | None:
    return db.get(Patient, patient_id)


def list_patients(
    db: Session,
    *,
    institution_id: int | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Patient]:
    stmt = select(Patient).order_by(Patient.created_at.desc())
    if institution_id is not None:
        stmt = stmt.where(Patient.institution_id == institution_id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Patient.full_name.ilike(like),
                Patient.hospital_number.ilike(like),
            )
        )
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))
