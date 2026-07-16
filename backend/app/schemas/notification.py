from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consultation_id: int | None
    kind: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int
