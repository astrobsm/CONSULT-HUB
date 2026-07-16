from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str,
    kind: str,
    institution_id: int | None = None,
    consultation_id: int | None = None,
    commit: bool = True,
) -> Notification:
    note = Notification(
        user_id=user_id,
        institution_id=institution_id,
        consultation_id=consultation_id,
        kind=kind,
        title=title,
        body=body,
    )
    db.add(note)
    if commit:
        db.commit()
        db.refresh(note)
        # Push a live signal so the recipient refreshes (post-commit).
        from app.core.realtime import manager

        manager.publish([user_id], {"type": "notification"})
    return note


def list_notifications(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return list(db.scalars(stmt.limit(limit)))


def unread_count(db: Session, *, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return db.scalar(stmt) or 0


def get_notification(db: Session, notification_id: int) -> Notification | None:
    return db.get(Notification, notification_id)


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, *, user_id: int) -> int:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
