from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import notification as crud
from app.models.entities import User
from app.schemas.notification import NotificationRead, UnreadCount

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationRead]:
    return crud.list_notifications(
        db, user_id=current_user.id, unread_only=unread_only, limit=limit
    )


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCount:
    return UnreadCount(unread=crud.unread_count(db, user_id=current_user.id))


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationRead:
    note = crud.get_notification(db, notification_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return crud.mark_read(db, note)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCount:
    crud.mark_all_read(db, user_id=current_user.id)
    return UnreadCount(unread=0)
