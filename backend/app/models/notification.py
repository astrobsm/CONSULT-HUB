from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.entities import utcnow


class Notification(Base):
    """An in-app notification addressed to a single user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    consultation_id: Mapped[int | None] = mapped_column(
        ForeignKey("consultations.id"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(40))  # escalation | status_change
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
