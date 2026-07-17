from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.scheduling_enums import (
    AppointmentStatus,
    AppointmentType,
    LoadBalancing,
    StationStatus,
    StationType,
    WaitingStatus,
)


# ---- Clinics ----

class ClinicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    department_id: int | None = None
    subspecialty: str | None = None
    location: str | None = None
    operating_days: str = "0,1,2,3,4"
    open_time: str = "08:00"
    close_time: str = "16:00"
    break_start: str | None = None
    break_end: str | None = None
    slot_duration_minutes: int = Field(default=20, ge=5, le=120)
    load_balancing: LoadBalancing = LoadBalancing.LEAST_BUSY


class ClinicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    subspecialty: str | None = None
    location: str | None = None
    operating_days: str | None = None
    open_time: str | None = None
    close_time: str | None = None
    break_start: str | None = None
    break_end: str | None = None
    slot_duration_minutes: int | None = Field(default=None, ge=5, le=120)
    load_balancing: LoadBalancing | None = None
    is_active: bool | None = None


class ClinicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int | None
    department_id: int | None
    name: str
    subspecialty: str | None
    location: str | None
    operating_days: str
    open_time: str
    close_time: str
    break_start: str | None
    break_end: str | None
    slot_duration_minutes: int
    load_balancing: LoadBalancing
    is_active: bool
    created_at: datetime


# ---- Stations ----

class StationCreate(BaseModel):
    station_number: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=150)
    station_type: StationType = StationType.CONSULTANT
    room_number: str | None = None
    assigned_user_id: int | None = None
    max_patients: int | None = Field(default=None, ge=1)


class StationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    station_type: StationType | None = None
    room_number: str | None = None
    assigned_user_id: int | None = None
    max_patients: int | None = Field(default=None, ge=1)
    status: StationStatus | None = None


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    station_number: int
    name: str
    station_type: StationType
    room_number: str | None
    assigned_user_id: int | None
    max_patients: int | None
    status: StationStatus


# ---- Availability ----

class StationAvailability(BaseModel):
    station_id: int
    station_name: str
    booked_count: int
    free_slots: list[datetime]


class AvailabilityRead(BaseModel):
    clinic_id: int
    date: str
    slot_duration_minutes: int
    stations: list[StationAvailability]


# ---- Holds ----

class HoldCreate(BaseModel):
    clinic_id: int
    slot_start: datetime
    station_id: int | None = None


class HoldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    slot_start: datetime
    expires_at: datetime


# ---- Appointments ----

class AppointmentCreate(BaseModel):
    clinic_id: int
    patient_id: int
    slot_start: datetime
    appointment_type: AppointmentType = AppointmentType.NEW_PATIENT
    station_id: int | None = None
    reason: str | None = None
    consultation_id: int | None = None


class AppointmentRead(BaseModel):
    id: int
    appointment_number: str | None
    check_in_code: str | None
    clinic_id: int
    clinic_name: str | None
    station_id: int
    station_name: str | None
    patient_id: int
    patient_name: str | None
    consultation_id: int | None
    appointment_type: AppointmentType
    slot_start: datetime
    duration_minutes: int
    status: AppointmentStatus
    queue_position: int | None
    reason: str | None
    rescheduled_to_id: int | None
    checked_in_at: datetime | None
    created_at: datetime


class AppointmentTransition(BaseModel):
    to_status: AppointmentStatus
    cancellation_reason: str | None = None


class RescheduleRequest(BaseModel):
    slot_start: datetime
    station_id: int | None = None


class CheckInRequest(BaseModel):
    code: str


class WaitingListCreate(BaseModel):
    patient_id: int
    target_date: datetime
    appointment_type: AppointmentType = AppointmentType.REVIEW


class WaitingListRead(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    patient_name: str | None
    target_date: datetime
    appointment_type: AppointmentType
    status: WaitingStatus
    promoted_appointment_id: int | None
    created_at: datetime
