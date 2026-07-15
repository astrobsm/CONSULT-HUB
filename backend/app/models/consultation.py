from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.entities import utcnow
from app.models.enums import ConsultationStatus, ConsultationType, Priority


class Consultation(Base):
    """A multidisciplinary consultation request and its workflow state."""

    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Tenancy / references (kept as optional FKs for the scaffold slice).
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patients.id"), nullable=True
    )
    requesting_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    target_department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )

    # Routing details (free text on the scaffold; FK-backed later).
    target_specialty: Mapped[str | None] = mapped_column(String(150), nullable=True)
    target_consultant: Mapped[str | None] = mapped_column(String(150), nullable=True)

    consultation_type: Mapped[ConsultationType] = mapped_column(
        default=ConsultationType.WARD
    )
    priority: Mapped[Priority] = mapped_column(default=Priority.ROUTINE)
    status: Mapped[ConsultationStatus] = mapped_column(
        default=ConsultationStatus.SUBMITTED, index=True
    )

    reason: Mapped[str] = mapped_column(String(500))
    clinical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    specific_questions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Required response window in minutes; drives escalation.
    required_response_minutes: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    events: Mapped[list[ConsultationEvent]] = relationship(
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="ConsultationEvent.created_at",
    )


class ConsultationEvent(Base):
    """Append-only audit/workflow event on a consultation."""

    __tablename__ = "consultation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    consultation_id: Mapped[int] = mapped_column(
        ForeignKey("consultations.id"), index=True
    )
    from_status: Mapped[ConsultationStatus | None] = mapped_column(nullable=True)
    to_status: Mapped[ConsultationStatus | None] = mapped_column(nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    consultation: Mapped[Consultation] = relationship(back_populates="events")
