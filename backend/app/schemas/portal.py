from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.scheduling_enums import AppointmentType


class PortalActivateRequest(BaseModel):
    hospital_number: str
    email: str


class PortalSetPassword(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class PatientPortalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    hospital_number: str
    email: str | None
    phone: str | None
    institution_id: int | None


class PortalToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient: PatientPortalRead


class PortalBook(BaseModel):
    clinic_id: int
    slot_start: datetime
    appointment_type: AppointmentType = AppointmentType.REVIEW
    station_id: int | None = None


class PortalReschedule(BaseModel):
    slot_start: datetime
    station_id: int | None = None


class PortalWaitingList(BaseModel):
    clinic_id: int
    target_date: datetime
    appointment_type: AppointmentType = AppointmentType.REVIEW
