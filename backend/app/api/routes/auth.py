from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.crud import user as crud_user
from app.models.entities import User
from app.schemas.auth import Token, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User) -> Token:
    token = create_access_token(
        user.id, extra={"role": user.role, "inst": user.institution_id}
    )
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.post(
    "/register", response_model=Token, status_code=status.HTTP_201_CREATED
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> Token:
    if crud_user.get_user_by_email(db, payload.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    user = crud_user.create_user(db, payload)
    return _issue_token(user)


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
