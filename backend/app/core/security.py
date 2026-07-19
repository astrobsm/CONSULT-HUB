"""Password hashing and JWT helpers.

Password hashing uses PBKDF2-HMAC-SHA256 from the standard library (zero native
dependencies, FIPS-approved). Swap for argon2/bcrypt via `argon2-cffi` or
`bcrypt` before production if a memory-hard KDF is required.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

_ALGO = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = settings.pbkdf2_iterations
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "${}${}${}${}".format(
        _ALGO,
        iterations,
        base64.b64encode(salt).decode(),
        base64.b64encode(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_b64, hash_b64 = stored.split("$")[-4:]
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )


def create_purpose_token(
    subject: str | int, purpose: str, minutes: int, token_version: int = 0
) -> str:
    """A short-lived, single-purpose token (password reset / invite / portal).

    Carries `typ="purpose"` so it can never be mistaken for an access token by
    the request authenticators (which require `typ` in {"staff", "patient"}),
    and `tv` (the subject's token version at issue) so it becomes invalid once
    it — or any later password change — bumps that version.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "typ": "purpose",
        "purpose": purpose,
        "tv": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(
        payload, settings.secret_key, algorithm=settings.jwt_algorithm
    )


def decode_purpose_token(
    token: str, allowed_purposes: set[str]
) -> dict[str, Any]:
    """Return the decoded payload if valid and its purpose is allowed."""
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("typ") != "purpose":
        raise jwt.InvalidTokenError("Not a purpose token")
    if payload.get("purpose") not in allowed_purposes:
        raise jwt.InvalidTokenError("Unexpected token purpose")
    return payload


def token_is_current(payload: dict[str, Any], token_version: int) -> bool:
    """False if the token's version is behind the subject's current version.

    Bumping the subject's `token_version` on a password change invalidates every
    outstanding token that embedded the old value — this ejects existing
    sessions and makes reset/invite/portal tokens single-use. Tokens minted
    before this claim existed default to version 0 (matching un-migrated rows),
    so a deploy doesn't force everyone to re-authenticate.
    """
    return int(payload.get("tv", 0)) == token_version
