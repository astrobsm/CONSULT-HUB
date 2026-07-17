from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.entities import Patient
from app.schemas.patient import PatientCreate


def get_patient_by_email(db: Session, email: str) -> Patient | None:
    """A portal-activated patient with this email (first match)."""
    return db.scalar(
        select(Patient)
        .where(
            Patient.email == email.lower(),
            Patient.hashed_password.isnot(None),
        )
        .order_by(Patient.id)
    )


def find_for_activation(
    db: Session, *, hospital_number: str, email: str
) -> Patient | None:
    """Match a patient by BOTH hospital number and the email on their record."""
    return db.scalar(
        select(Patient).where(
            Patient.hospital_number == hospital_number,
            Patient.email == email.lower(),
        )
    )


def authenticate_patient(
    db: Session, email: str, password: str
) -> Patient | None:
    patient = get_patient_by_email(db, email.lower())
    if patient is None or not patient.hashed_password:
        return None
    if not verify_password(password, patient.hashed_password):
        return None
    return patient


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
