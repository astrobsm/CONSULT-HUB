from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)


class InstitutionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    motto: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    primary_color: str | None = None


class InstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    motto: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    primary_color: str | None = None
    has_logo: bool = False
    has_watermark: bool = False
    created_at: datetime


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    specialty: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    specialty: str | None = None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    name: str
    specialty: str | None
