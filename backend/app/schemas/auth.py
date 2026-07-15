from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Permissive: hospital intranets legitimately use domains like `.local`, so we
# do a syntactic check only rather than deliverable-domain validation.
_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(pattern=_EMAIL_RE, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str = "registrar"
    designation: str | None = None
    institution_id: int | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    designation: str | None
    institution_id: int | None
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
