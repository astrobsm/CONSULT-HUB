from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import ADMIN_ROLES, SUPER_ADMIN
from app.core.security import decode_access_token
from app.core.database import get_db
from app.models.entities import Patient, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/auth/login"
)

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise _credentials_exc

    # Patient portal tokens must never authenticate a staff request.
    if payload.get("typ") == "patient":
        raise _credentials_exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_exc
    return user


def get_current_patient(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Patient:
    """Authenticate a patient-portal request. Rejects staff tokens."""
    try:
        payload = decode_access_token(token)
        patient_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise _credentials_exc

    if payload.get("typ") != "patient":
        raise _credentials_exc

    patient = db.get(Patient, patient_id)
    if patient is None or not patient.hashed_password:
        raise _credentials_exc
    return patient


def require_roles(*roles: str) -> Callable[[User], User]:
    """Dependency factory: allow only users whose role is in `roles`."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if roles and current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return current_user

    return checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow only super/institution admins."""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


def assert_can_manage_institution(actor: User, institution_id: int | None) -> None:
    """A super admin manages any tenant; others only their own."""
    if actor.role == SUPER_ADMIN:
        return
    if institution_id is not None and actor.institution_id == institution_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only manage your own institution",
    )
