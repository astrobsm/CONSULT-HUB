from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consultation import Consultation, ConsultationEvent
from app.models.enums import STATUS_TRANSITIONS, ConsultationStatus
from app.schemas.consultation import ConsultationCreate


class InvalidTransition(Exception):
    """Raised when a requested workflow transition is not allowed."""


def create_consultation(
    db: Session,
    payload: ConsultationCreate,
    *,
    requesting_user_id: int,
    institution_id: int | None,
) -> Consultation:
    consultation = Consultation(
        **payload.model_dump(),
        requesting_user_id=requesting_user_id,
        institution_id=institution_id,
        status=ConsultationStatus.SUBMITTED,
    )
    db.add(consultation)
    db.flush()  # assign an id before logging the event

    db.add(
        ConsultationEvent(
            consultation_id=consultation.id,
            from_status=None,
            to_status=ConsultationStatus.SUBMITTED,
            actor_user_id=requesting_user_id,
            note="Consultation submitted",
        )
    )
    db.commit()
    db.refresh(consultation)
    return consultation


def get_consultation(db: Session, consultation_id: int) -> Consultation | None:
    return db.get(Consultation, consultation_id)


def list_consultations(
    db: Session,
    *,
    institution_id: int | None = None,
    patient_id: int | None = None,
    status: ConsultationStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Consultation]:
    stmt = select(Consultation).order_by(Consultation.created_at.desc())
    if institution_id is not None:
        stmt = stmt.where(Consultation.institution_id == institution_id)
    if patient_id is not None:
        stmt = stmt.where(Consultation.patient_id == patient_id)
    if status is not None:
        stmt = stmt.where(Consultation.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def transition_consultation(
    db: Session,
    consultation: Consultation,
    *,
    to_status: ConsultationStatus,
    actor_user_id: int | None = None,
    note: str | None = None,
) -> Consultation:
    allowed = STATUS_TRANSITIONS.get(consultation.status, set())
    if to_status not in allowed:
        raise InvalidTransition(
            f"Cannot move consultation from '{consultation.status.value}' "
            f"to '{to_status.value}'."
        )

    from_status = consultation.status
    consultation.status = to_status

    now = datetime.now(timezone.utc)
    if to_status == ConsultationStatus.ACKNOWLEDGED and not consultation.acknowledged_at:
        consultation.acknowledged_at = now
    if to_status == ConsultationStatus.COMPLETED:
        consultation.completed_at = now

    db.add(
        ConsultationEvent(
            consultation_id=consultation.id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            note=note,
        )
    )
    db.commit()
    db.refresh(consultation)
    return consultation
