from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.entities import utcnow
from app.models.scheduling_enums import (
    AppointmentStatus,
    AppointmentType,
    LoadBalancing,
    StationStatus,
    StationType,
)


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150))
    subspecialty: Mapped[str | None] = mapped_column(String(150), nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Operating config. Times are local wall-clock "HH:MM"; days are Python
    # weekday ints (Mon=0) as a CSV, e.g. "0,1,2,3,4".
    operating_days: Mapped[str] = mapped_column(String(30), default="0,1,2,3,4")
    open_time: Mapped[str] = mapped_column(String(5), default="08:00")
    close_time: Mapped[str] = mapped_column(String(5), default="16:00")
    break_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    break_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    slot_duration_minutes: Mapped[int] = mapped_column(default=20)

    load_balancing: Mapped[LoadBalancing] = mapped_column(
        default=LoadBalancing.LEAST_BUSY
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    stations: Mapped[list[ConsultationStation]] = relationship(
        back_populates="clinic",
        cascade="all, delete-orphan",
        order_by="ConsultationStation.station_number",
    )

    @property
    def operating_weekdays(self) -> set[int]:
        return {
            int(d) for d in self.operating_days.split(",") if d.strip().isdigit()
        }


class ConsultationStation(Base):
    __tablename__ = "consultation_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    station_number: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String(150))
    station_type: Mapped[StationType] = mapped_column(
        default=StationType.CONSULTANT
    )
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    max_patients: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[StationStatus] = mapped_column(default=StationStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    clinic: Mapped[Clinic] = relationship(back_populates="stations")


class Appointment(Base):
    __tablename__ = "appointments"

    # Bulletproof no-double-book: at most one *active* appointment per
    # (station, slot_start). The predicate uses the enum MEMBER NAMES, since
    # SQLAlchemy stores the Enum column by name.
    __table_args__ = (
        Index(
            "uq_station_slot_active",
            "station_id",
            "slot_start",
            unique=True,
            sqlite_where=text(
                "status NOT IN ('CANCELLED', 'RESCHEDULED')"
            ),
            postgresql_where=text(
                "status NOT IN ('CANCELLED', 'RESCHEDULED')"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("consultation_stations.id"), index=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    # Optional bridge to an inpatient/interdepartmental consult.
    consultation_id: Mapped[int | None] = mapped_column(
        ForeignKey("consultations.id"), nullable=True
    )

    appointment_number: Mapped[str | None] = mapped_column(
        String(40), nullable=True, index=True
    )
    appointment_type: Mapped[AppointmentType] = mapped_column(
        default=AppointmentType.NEW_PATIENT
    )
    slot_start: Mapped[datetime] = mapped_column(index=True)
    duration_minutes: Mapped[int] = mapped_column(default=20)
    status: Mapped[AppointmentStatus] = mapped_column(
        default=AppointmentStatus.BOOKED, index=True
    )
    queue_position: Mapped[int | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )
    # When rescheduled, points to the replacement appointment (history).
    rescheduled_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id"), nullable=True
    )

    booked_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow, onupdate=utcnow
    )


class SlotHold(Base):
    """A short-lived reservation of a station+slot while a booking completes."""

    __tablename__ = "slot_holds"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    station_id: Mapped[int] = mapped_column(
        ForeignKey("consultation_stations.id"), index=True
    )
    slot_start: Mapped[datetime] = mapped_column(index=True)
    held_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
