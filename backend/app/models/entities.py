from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Institution(Base):
    """A tenant hospital / health institution."""

    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    departments: Mapped[list[Department]] = relationship(
        back_populates="institution", cascade="all, delete-orphan"
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    name: Mapped[str] = mapped_column(String(150))
    specialty: Mapped[str | None] = mapped_column(String(150), nullable=True)

    institution: Mapped[Institution] = relationship(
        back_populates="departments"
    )


class User(Base):
    """Staff member (doctor, nurse, allied health, admin)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="registrar")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    hospital_number: Mapped[str] = mapped_column(String(50), index=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    genotype: Mapped[str | None] = mapped_column(String(10), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    height_cm: Mapped[float | None] = mapped_column(nullable=True)
    ward: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    primary_diagnosis: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )
    allergies: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
