from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsultationStatus, ConsultationType, Priority


class ConsultationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: ConsultationStatus | None
    to_status: ConsultationStatus | None
    actor_user_id: int | None
    note: str | None
    created_at: datetime


class EscalationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: int
    label: str
    threshold_minutes: int
    notify_role: str
    fired_at: datetime


class ConsultationCreate(BaseModel):
    """Client payload. institution_id / requesting_user_id come from the token."""

    patient_id: int | None = None
    target_department_id: int | None = None
    target_specialty: str | None = None
    target_consultant: str | None = None
    consultation_type: ConsultationType = ConsultationType.WARD
    priority: Priority = Priority.ROUTINE
    reason: str = Field(min_length=1, max_length=500)
    clinical_summary: str | None = None
    specific_questions: str | None = None
    required_response_minutes: int | None = Field(default=None, ge=1)


class ConsultationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int | None
    requesting_user_id: int | None
    institution_id: int | None
    target_department_id: int | None
    target_specialty: str | None
    target_consultant: str | None
    consultation_type: ConsultationType
    priority: Priority
    reason: str
    clinical_summary: str | None
    specific_questions: str | None
    required_response_minutes: int | None
    status: ConsultationStatus
    escalation_level: int
    created_at: datetime
    updated_at: datetime
    acknowledged_at: datetime | None
    completed_at: datetime | None
    events: list[ConsultationEventRead] = []
    escalation_events: list[EscalationEventRead] = []


class ConsultationTransition(BaseModel):
    """Request a workflow-state change."""

    to_status: ConsultationStatus
    actor_user_id: int | None = None
    note: str | None = None
