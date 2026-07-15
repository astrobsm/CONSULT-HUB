from __future__ import annotations

from pydantic import BaseModel


class SpecialtyCount(BaseModel):
    specialty: str
    count: int


class DashboardSummary(BaseModel):
    total: int
    pending: int
    today: int
    completed: int
    overdue: int
    completion_rate: float
    avg_ack_minutes: float | None
    avg_completion_minutes: float | None
    by_priority_pending: dict[str, int]
    by_status: dict[str, int]
    top_specialties: list[SpecialtyCount]
