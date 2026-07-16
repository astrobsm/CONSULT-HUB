"""Timed escalation engine.

`run_escalations` is a pure function of (db, now): it scans unacknowledged,
non-terminal consultations and fires every escalation threshold each has crossed
since it was created, recording an auditable event per level. Because `now` is
injectable, the engine is deterministically testable without waiting on the clock.

Notification delivery (push / SMS / email / WhatsApp per the spec) is stubbed by
`_notify`, which logs — wire it to a real transport later. The scheduler
(APScheduler, started in the app lifespan) simply calls this on an interval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consultation import (
    Consultation,
    ConsultationEvent,
    EscalationEvent,
)
from app.models.enums import TERMINAL_STATUSES

logger = logging.getLogger("consulthub.escalation")


@dataclass(frozen=True)
class EscalationStep:
    level: int
    minutes: int
    label: str
    notify_role: str


# Default policy (spec: 15/30/60/90/120 min). Configurable per tenant later.
DEFAULT_POLICY: tuple[EscalationStep, ...] = (
    EscalationStep(1, 15, "First reminder", "assigned"),
    EscalationStep(2, 30, "Second reminder", "assigned"),
    EscalationStep(3, 60, "Escalate to consultant", "consultant"),
    EscalationStep(4, 90, "Escalate to HOD", "hod"),
    EscalationStep(5, 120, "Escalate to Medical Director", "medical_director"),
)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _fire(
    db: Session,
    consultation: Consultation,
    step: EscalationStep,
    now: datetime,
) -> list[int]:
    # Imported here to avoid a circular import at module load.
    from app.services.notifications import notify_escalation

    logger.warning(
        "ESCALATION consult#%s L%s '%s' -> notify %s",
        consultation.id,
        step.level,
        step.label,
        step.notify_role,
    )
    db.add(
        EscalationEvent(
            consultation_id=consultation.id,
            level=step.level,
            label=step.label,
            threshold_minutes=step.minutes,
            notify_role=step.notify_role,
            fired_at=now,
        )
    )
    db.add(
        ConsultationEvent(
            consultation_id=consultation.id,
            from_status=consultation.status,
            to_status=consultation.status,
            actor_user_id=None,  # system
            note=f"Escalation L{step.level}: {step.label}",
        )
    )
    consultation.escalation_level = step.level
    return notify_escalation(
        db,
        consultation,
        level=step.level,
        label=step.label,
        threshold_minutes=step.minutes,
        notify_role=step.notify_role,
    )


def run_escalations(
    db: Session,
    now: datetime | None = None,
    policy: tuple[EscalationStep, ...] = DEFAULT_POLICY,
) -> list[dict]:
    """Fire all due escalation levels. Returns the events fired this run."""
    now = now or datetime.now(timezone.utc)

    stmt = select(Consultation).where(
        Consultation.acknowledged_at.is_(None),
        Consultation.status.notin_(TERMINAL_STATUSES),
    )

    fired: list[dict] = []
    notified: set[int] = set()
    for consultation in db.scalars(stmt):
        elapsed_min = (
            now - _as_utc(consultation.created_at)
        ).total_seconds() / 60
        for step in policy:
            if consultation.escalation_level >= step.level:
                continue
            if elapsed_min >= step.minutes:
                notified.update(_fire(db, consultation, step, now))
                fired.append(
                    {
                        "consultation_id": consultation.id,
                        "level": step.level,
                        "label": step.label,
                    }
                )

    if fired:
        db.commit()
        # Push realtime signals only after the transaction is durable.
        from app.core.realtime import manager

        manager.publish(notified, {"type": "notification"})
    return fired


def run_escalations_job() -> None:
    """Entry point for the scheduler: owns its own DB session."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        fired = run_escalations(db)
        if fired:
            logger.info("Escalation run fired %d event(s)", len(fired))
    except Exception:  # never let a bad run kill the scheduler thread
        logger.exception("Escalation run failed")
    finally:
        db.close()
