from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment


def create_attachment(
    db: Session,
    *,
    consultation_id: int,
    institution_id: int | None,
    uploaded_by_user_id: int | None,
    filename: str,
    storage_key: str,
    content_type: str,
    size_bytes: int,
) -> Attachment:
    att = Attachment(
        consultation_id=consultation_id,
        institution_id=institution_id,
        uploaded_by_user_id=uploaded_by_user_id,
        filename=filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


def list_for_consultation(
    db: Session, consultation_id: int
) -> list[Attachment]:
    stmt = (
        select(Attachment)
        .where(Attachment.consultation_id == consultation_id)
        .order_by(Attachment.created_at.desc())
    )
    return list(db.scalars(stmt))


def get_attachment(db: Session, attachment_id: int) -> Attachment | None:
    return db.get(Attachment, attachment_id)


def delete_attachment(db: Session, attachment: Attachment) -> None:
    db.delete(attachment)
    db.commit()
