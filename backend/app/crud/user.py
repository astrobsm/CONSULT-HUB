from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.entities import User
from app.schemas.user import UserCreate, UserUpdate


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def list_users(
    db: Session,
    *,
    institution_id: int | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[User]:
    stmt = select(User).order_by(User.full_name)
    if institution_id is not None:
        stmt = stmt.where(User.institution_id == institution_id)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def create_user(
    db: Session, payload: UserCreate, *, institution_id: int | None
) -> User:
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        designation=payload.designation,
        department_id=payload.department_id,
        institution_id=institution_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email.lower())
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
