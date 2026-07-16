"""Email transport.

When `SMTP_HOST` is configured, sends via SMTP; otherwise logs the message
(console transport) so the app is fully functional in dev without a mail server.
Always best-effort: a failure is logged, never raised, so it can't break the
request or the escalation run.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("consulthub.email")


def send_email(to: str, subject: str, body: str) -> bool:
    """Send (or log) an email. Returns True if handed off without error."""
    if not to:
        return False

    if not settings.smtp_host:
        logger.info(
            "EMAIL (console) to=%s | %s\n%s", to, subject, body
        )
        return True

    try:
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            if settings.smtp_tls:
                s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password or "")
            s.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False
