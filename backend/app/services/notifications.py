"""Notification service.

Turns domain events (escalation fired, consultation status changed) into in-app
notifications and best-effort emails. Recipient resolution lives here so both the
background escalation engine and the request-path routes share one policy.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.email import send_email
from app.crud import notification as crud
from app.models.consultation import Consultation
from app.models.entities import User
from app.models.enums import ConsultationStatus

# Roles treated as senior escalation targets (HOD / Medical Director proxies).
_SENIOR_ROLES = {"institution_admin", "department_admin", "consultant"}


def _institution_users(db: Session, institution_id: int | None) -> list[User]:
    if institution_id is None:
        return []
    return list(
        db.scalars(select(User).where(User.institution_id == institution_id))
    )


def _escalation_recipients(
    db: Session, consultation: Consultation, notify_role: str, level: int
) -> list[User]:
    recipients: dict[int, User] = {}

    if consultation.requesting_user_id:
        requester = db.get(User, consultation.requesting_user_id)
        if requester:
            recipients[requester.id] = requester

    for user in _institution_users(db, consultation.institution_id):
        if user.role == notify_role or (level >= 3 and user.role in _SENIOR_ROLES):
            recipients[user.id] = user

    return list(recipients.values())


def notify_escalation(
    db: Session,
    consultation: Consultation,
    *,
    level: int,
    label: str,
    threshold_minutes: int,
    notify_role: str,
) -> None:
    """Create in-app notifications and send emails for one escalation step."""
    title = f"Escalation L{level}: consult #{consultation.id}"
    body = (
        f"{label} — consultation #{consultation.id} "
        f'("{consultation.reason}") has gone {threshold_minutes} min without '
        f"acknowledgement. Priority: {consultation.priority.value}."
    )

    for user in _escalation_recipients(db, consultation, notify_role, level):
        crud.create_notification(
            db,
            user_id=user.id,
            institution_id=consultation.institution_id,
            consultation_id=consultation.id,
            kind="escalation",
            title=title,
            body=body,
            commit=False,  # committed by the escalation run
        )
        if user.email:
            send_email(user.email, title, body)


def notify_new_message(
    db: Session,
    consultation: Consultation,
    *,
    sender_id: int,
    sender_name: str,
    body: str,
    participant_ids: set[int],
) -> None:
    """Notify the requester and prior thread participants (except the sender)."""
    recipients: set[int] = set(participant_ids)
    if consultation.requesting_user_id:
        recipients.add(consultation.requesting_user_id)
    recipients.discard(sender_id)

    preview = body if len(body) <= 140 else body[:137] + "…"
    for user_id in recipients:
        crud.create_notification(
            db,
            user_id=user_id,
            institution_id=consultation.institution_id,
            consultation_id=consultation.id,
            kind="message",
            title=f"New message on consult #{consultation.id}",
            body=f"{sender_name}: {preview}",
        )


# Status changes worth telling the requester about.
_NOTIFY_STATUSES = {
    ConsultationStatus.ACKNOWLEDGED,
    ConsultationStatus.ACCEPTED,
    ConsultationStatus.SEEN,
    ConsultationStatus.COMPLETED,
    ConsultationStatus.REJECTED,
    ConsultationStatus.RETURNED,
}


def notify_status_change(
    db: Session,
    consultation: Consultation,
    *,
    to_status: ConsultationStatus,
    actor_user_id: int | None,
) -> None:
    """In-app notify the requester when their consult changes state."""
    if to_status not in _NOTIFY_STATUSES:
        return
    requester_id = consultation.requesting_user_id
    if not requester_id or requester_id == actor_user_id:
        return

    crud.create_notification(
        db,
        user_id=requester_id,
        institution_id=consultation.institution_id,
        consultation_id=consultation.id,
        kind="status_change",
        title=f"Consult #{consultation.id} {to_status.value}",
        body=(
            f'Your consultation #{consultation.id} ("{consultation.reason}") '
            f"is now {to_status.value}."
        ),
    )
