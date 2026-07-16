from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import secrets

from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.roles import ALL_ROLES, SUPER_ADMIN
from app.core.security import create_purpose_token
from app.crud import user as crud
from app.models.entities import User
from app.schemas.auth import UserRead
from app.schemas.user import UserCreate, UserInvite, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _guard_target(actor: User, target: User) -> None:
    """A non-super admin may only touch users in their own institution."""
    if actor.role == SUPER_ADMIN:
        return
    if target.institution_id != actor.institution_id:
        raise HTTPException(status_code=404, detail="User not found")


def _guard_role_assignment(actor: User, role: str) -> None:
    """Only a super admin may create or grant the super_admin role."""
    if role == SUPER_ADMIN and actor.role != SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a super admin can assign the super_admin role",
        )


@router.get("/roles", response_model=list[str])
def list_roles(_: User = Depends(get_current_user)) -> list[str]:
    return ALL_ROLES


@router.get("", response_model=list[UserRead])
def list_users(
    institution_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[UserRead]:
    # Non-super admins are always scoped to their own institution.
    scope = (
        institution_id if admin.role == SUPER_ADMIN else admin.institution_id
    )
    return crud.list_users(db, institution_id=scope)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    if crud.get_user_by_email(db, payload.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    _guard_role_assignment(admin, payload.role)

    # Super admins may target any institution; others create in their own.
    institution_id = (
        payload.institution_id
        if admin.role == SUPER_ADMIN
        else admin.institution_id
    )
    return crud.create_user(db, payload, institution_id=institution_id)


@router.post(
    "/invite", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def invite_user(
    payload: UserInvite,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    if crud.get_user_by_email(db, payload.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    _guard_role_assignment(admin, payload.role)
    institution_id = (
        payload.institution_id
        if admin.role == SUPER_ADMIN
        else admin.institution_id
    )
    # Create with an unguessable placeholder password; the invitee sets a real
    # one via the emailed link.
    user = crud.create_user(
        db,
        UserCreate(
            full_name=payload.full_name,
            email=payload.email,
            password=secrets.token_urlsafe(24),
            role=payload.role,
            designation=payload.designation,
            department_id=payload.department_id,
        ),
        institution_id=institution_id,
    )
    token = create_purpose_token(
        user.id, "invite", settings.invite_token_expire_minutes
    )
    link = f"{settings.frontend_base_url}/set-password?token={token}"
    send_email(
        user.email,
        "You're invited to ConsultHUB",
        f"An administrator invited you to ConsultHUB. Set your password to "
        f"get started:\n\n{link}",
    )
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    _guard_target(admin, user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    _guard_target(admin, user)
    if payload.role is not None:
        _guard_role_assignment(admin, payload.role)
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    return crud.update_user(db, user, payload)
