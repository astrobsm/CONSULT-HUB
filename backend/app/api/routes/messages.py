from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import consultation as crud_consultation
from app.crud import message as crud
from app.models.entities import User
from app.schemas.message import MessageCreate, MessageRead
from app.services.notifications import notify_new_message

router = APIRouter(tags=["messages"])


def _scoped_consultation(consultation_id: int, db: Session, user: User):
    c = crud_consultation.get_consultation(db, consultation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if user.institution_id is not None and c.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return c


@router.get(
    "/consultations/{consultation_id}/messages",
    response_model=list[MessageRead],
)
def list_messages(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageRead]:
    _scoped_consultation(consultation_id, db, current_user)
    return crud.list_for_consultation(db, consultation_id)


@router.post(
    "/consultations/{consultation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    consultation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    consultation = _scoped_consultation(consultation_id, db, current_user)

    # Snapshot prior participants before adding the new message.
    prior = crud.participant_ids(db, consultation_id)

    msg = crud.create_message(
        db,
        consultation_id=consultation_id,
        institution_id=consultation.institution_id,
        sender_user_id=current_user.id,
        body=payload.body,
    )

    notify_new_message(
        db,
        consultation,
        sender_id=current_user.id,
        sender_name=current_user.full_name,
        body=payload.body,
        participant_ids=prior,
    )

    return {
        "id": msg.id,
        "consultation_id": msg.consultation_id,
        "sender_user_id": msg.sender_user_id,
        "sender_name": current_user.full_name,
        "body": msg.body,
        "created_at": msg.created_at,
    }
