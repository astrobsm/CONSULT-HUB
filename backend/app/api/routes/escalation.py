from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.escalation import DEFAULT_POLICY
from app.models.entities import User

router = APIRouter(prefix="/escalation", tags=["escalation"])


class EscalationStepRead(BaseModel):
    level: int
    minutes: int
    label: str
    notify_role: str


@router.get("/policy", response_model=list[EscalationStepRead])
def get_policy(
    _: User = Depends(get_current_user),
) -> list[EscalationStepRead]:
    return [
        EscalationStepRead(
            level=s.level,
            minutes=s.minutes,
            label=s.label,
            notify_role=s.notify_role,
        )
        for s in DEFAULT_POLICY
    ]
