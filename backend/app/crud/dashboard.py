"""Dashboard metrics.

For the scaffold this loads the tenant's consultations and aggregates in
Python — correct and readable at dev scale. Move the aggregation into SQL
(GROUP BY / window functions, or a materialized rollup) before large tenants.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.models.enums import TERMINAL_STATUSES, ConsultationStatus, Priority

TERMINAL = TERMINAL_STATUSES


def _as_utc(dt: datetime) -> datetime:
    """Treat naive timestamps (SQLite) as UTC for safe arithmetic."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def dashboard_summary(
    db: Session, *, institution_id: int | None
) -> dict:
    stmt = select(Consultation)
    if institution_id is not None:
        stmt = stmt.where(Consultation.institution_id == institution_id)
    consults = list(db.scalars(stmt))

    now = datetime.now(timezone.utc)
    today = now.date()

    total = len(consults)
    pending = [c for c in consults if c.status not in TERMINAL]
    completed = [c for c in consults if c.status == ConsultationStatus.COMPLETED]

    by_status: Counter[str] = Counter(c.status.value for c in consults)
    by_priority_pending: Counter[str] = Counter(
        c.priority.value for c in pending
    )

    ack_minutes = [
        (_as_utc(c.acknowledged_at) - _as_utc(c.created_at)).total_seconds() / 60
        for c in consults
        if c.acknowledged_at is not None
    ]
    completion_minutes = [
        (_as_utc(c.completed_at) - _as_utc(c.created_at)).total_seconds() / 60
        for c in completed
        if c.completed_at is not None
    ]

    overdue = 0
    for c in pending:
        if c.required_response_minutes is None or c.acknowledged_at is not None:
            continue
        elapsed = (now - _as_utc(c.created_at)).total_seconds() / 60
        if elapsed > c.required_response_minutes:
            overdue += 1

    escalated = sum(1 for c in pending if c.escalation_level > 0)

    specialty_counts = Counter(
        c.target_specialty for c in consults if c.target_specialty
    )
    top_specialties = [
        {"specialty": name, "count": count}
        for name, count in specialty_counts.most_common(5)
    ]

    def avg(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    return {
        "total": total,
        "pending": len(pending),
        "today": sum(1 for c in consults if _as_utc(c.created_at).date() == today),
        "completed": len(completed),
        "overdue": overdue,
        "escalated": escalated,
        "completion_rate": round(len(completed) / total, 3) if total else 0.0,
        "avg_ack_minutes": avg(ack_minutes),
        "avg_completion_minutes": avg(completion_minutes),
        "by_priority_pending": {
            p.value: by_priority_pending.get(p.value, 0) for p in Priority
        },
        "by_status": {
            s.value: by_status.get(s.value, 0)
            for s in ConsultationStatus
            if by_status.get(s.value, 0) > 0
        },
        "top_specialties": top_specialties,
    }
