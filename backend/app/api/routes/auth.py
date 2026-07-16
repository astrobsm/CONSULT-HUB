from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import jwt

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import (
    create_access_token,
    create_purpose_token,
    decode_purpose_token,
    hash_password,
    verify_password,
)
from app.crud import user as crud_user
from app.models.entities import User
from app.schemas.auth import (
    ChangePassword,
    PasswordResetRequest,
    PasswordSetConfirm,
    ProfileUpdate,
    Token,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User) -> Token:
    token = create_access_token(
        user.id, extra={"role": user.role, "inst": user.institution_id}
    )
    return Token(access_token=token, user=UserRead.model_validate(user))


# Note: self-registration is intentionally disabled. Admins create users via
# POST /api/users. The first admin is created by the seed script.


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    # OAuth2 form uses `username`; we treat it as the email.
    user = crud_user.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_token(user)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()


def _set_password_link(token: str) -> str:
    return f"{settings.frontend_base_url}/set-password?token={token}"


@router.post(
    "/password-reset/request", status_code=status.HTTP_202_ACCEPTED
)
def request_password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    # Always return 202 — never reveal whether an email is registered.
    user = crud_user.get_user_by_email(db, payload.email.strip().lower())
    if user and user.is_active:
        token = create_purpose_token(
            user.id, "reset", settings.reset_token_expire_minutes
        )
        send_email(
            user.email,
            "Reset your ConsultHUB password",
            "A password reset was requested for your account. Set a new "
            f"password here:\n\n{_set_password_link(token)}\n\n"
            "If you didn't request this, ignore this email.",
        )
    return {"status": "accepted"}


@router.post(
    "/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT
)
def confirm_password_reset(
    payload: PasswordSetConfirm, db: Session = Depends(get_db)
) -> None:
    # Accepts both reset and invite tokens (both set a password).
    try:
        user_id = decode_purpose_token(payload.token, {"reset", "invite"})
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    user = crud_user.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    user.hashed_password = hash_password(payload.new_password)
    user.is_active = True  # accepting an invite activates the account
    db.commit()
