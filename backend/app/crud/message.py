from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.message import ConsultationMessage


def create_message(
    db: Session,
    *,
    consultation_id: int,
    institution_id: int | None,
    sender_user_id: int,
    body: str,
) -> ConsultationMessage:
    msg = ConsultationMessage(
        consultation_id=consultation_id,
        institution_id=institution_id,
        sender_user_id=sender_user_id,
        body=body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def list_for_consultation(
    db: Session, consultation_id: int
) -> list[dict]:
    """Return messages (oldest first) with the sender's display name."""
    stmt = (
        select(ConsultationMessage, User.full_name)
        .join(User, User.id == ConsultationMessage.sender_user_id)
        .where(ConsultationMessage.consultation_id == consultation_id)
        .order_by(ConsultationMessage.created_at)
    )
    out: list[dict] = []
    for msg, sender_name in db.execute(stmt):
        out.append(
            {
                "id": msg.id,
                "consultation_id": msg.consultation_id,
                "sender_user_id": msg.sender_user_id,
                "sender_name": sender_name,
                "body": msg.body,
                "created_at": msg.created_at,
            }
        )
    return out


def participant_ids(db: Session, consultation_id: int) -> set[int]:
    """Distinct users who have posted in the thread."""
    stmt = select(ConsultationMessage.sender_user_id).where(
        ConsultationMessage.consultation_id == consultation_id
    )
    return set(db.scalars(stmt))
