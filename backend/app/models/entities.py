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
    # Branding.
    motto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    website: Mapped[str | None] = mapped_column(String(150), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    watermark_key: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
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
    # Bumped on every password change/reset. Tokens embed the value current at
    # issue; a mismatch is rejected — this invalidates outstanding sessions and
    # makes reset/invite tokens single-use once they set a password.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
    # Appearance preferences.
    theme: Mapped[str] = mapped_column(
        String(10), default="system", server_default="system"
    )
    accent: Mapped[str] = mapped_column(
        String(20), default="blue", server_default="blue"
    )
    font_family: Mapped[str] = mapped_column(
        String(20), default="system", server_default="system"
    )
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
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Set when the patient activates their self-service portal account.
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    # Bumped on portal password set/change; stale portal tokens are rejected.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
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
