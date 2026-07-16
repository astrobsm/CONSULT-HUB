from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.entities import utcnow


class ConsultationMessage(Base):
    """A message in a consultation's secure discussion thread."""

    __tablename__ = "consultation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    consultation_id: Mapped[int] = mapped_column(
        ForeignKey("consultations.id"), index=True
    )
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
