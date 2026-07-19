"""SMS and WhatsApp transports (Twilio).

Mirrors the email transport: when Twilio credentials are configured, sends via
the Twilio REST API; otherwise logs the message to the console so the app is
fully functional in dev. Always best-effort — a failure is logged, never raised.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("consulthub.sms")

_TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _mask(number: str) -> str:
    """Redact a phone number for logs: '+2348012345678' -> '+234****5678'."""
    if len(number) <= 8:
        return "****"
    return f"{number[:4]}****{number[-4:]}"


def _log_console(kind: str, to: str, body: str) -> None:
    if settings.debug:
        logger.warning("%s (console, no Twilio) to=%s | %s", kind, to, body)
    else:
        logger.warning(
            "%s (console, no Twilio) to=%s [body redacted]", kind, _mask(to)
        )


def _twilio_configured() -> bool:
    return bool(
        settings.twilio_account_sid and settings.twilio_auth_token
    )


def _send_twilio(from_: str | None, to: str, body: str) -> bool:
    if not from_:
        logger.warning("Twilio 'from' not configured; message dropped")
        return False
    url = _TWILIO_URL.format(sid=settings.twilio_account_sid)
    try:
        resp = httpx.post(
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={"From": from_, "To": to, "Body": body},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Twilio send failed to %s", to)
        return False


def send_sms(to: str | None, body: str) -> bool:
    if not to:
        return False
    if _twilio_configured():
        return _send_twilio(settings.twilio_sms_from, to, body)
    _log_console("SMS", to, body)
    return True


def send_whatsapp(to: str | None, body: str) -> bool:
    if not to:
        return False
    target = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    if _twilio_configured():
        return _send_twilio(settings.twilio_whatsapp_from, target, body)
    _log_console("WHATSAPP", target, body)
    return True
