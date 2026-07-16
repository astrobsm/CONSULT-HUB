from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.roles import is_valid_role

_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(pattern=_EMAIL_RE, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str = "registrar"
    designation: str | None = None
    department_id: int | None = None
    # Honoured only for super admins; others get their own institution.
    institution_id: int | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if not is_valid_role(v):
            raise ValueError(f"Unknown role: {v}")
        return v


class UserUpdate(BaseModel):
    role: str | None = None
    designation: str | None = None
    department_id: int | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_role(v):
            raise ValueError(f"Unknown role: {v}")
        return v
