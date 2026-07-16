from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    assert_can_manage_institution,
    get_current_user,
    require_admin,
)
from app.core.database import get_db
from app.core.roles import SUPER_ADMIN
from app.crud import org as crud
from app.models.entities import Department, User
from app.schemas.org import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    InstitutionCreate,
    InstitutionRead,
)

router = APIRouter(tags=["org"])


# ---- Institutions ----

@router.get("/institutions", response_model=list[InstitutionRead])
def list_institutions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InstitutionRead]:
    # Super admins see all; everyone else sees only their own institution.
    if current_user.role == SUPER_ADMIN:
        return crud.list_institutions(db)
    if current_user.institution_id is None:
        return []
    inst = crud.get_institution(db, current_user.institution_id)
    return [inst] if inst else []


@router.post(
    "/institutions",
    response_model=InstitutionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> InstitutionRead:
    # Only super admins may create tenants.
    if admin.role != SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a super admin can create institutions",
        )
    if crud.get_institution_by_code(db, payload.code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An institution with this code already exists",
        )
    return crud.create_institution(db, payload)


# ---- Departments ----

@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(
    institution_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DepartmentRead]:
    scope = (
        institution_id
        if current_user.role == SUPER_ADMIN
        else current_user.institution_id
    )
    return crud.list_departments(db, institution_id=scope)


@router.post(
    "/departments",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_department(
    payload: DepartmentCreate,
    institution_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DepartmentRead:
    target = (
        institution_id
        if admin.role == SUPER_ADMIN and institution_id is not None
        else admin.institution_id
    )
    if target is None:
        raise HTTPException(status_code=400, detail="No institution specified")
    assert_can_manage_institution(admin, target)
    return crud.create_department(db, payload, institution_id=target)


def _get_dept_scoped(
    department_id: int, db: Session, admin: User
) -> Department:
    dept = crud.get_department(db, department_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found")
    if (
        admin.role != SUPER_ADMIN
        and dept.institution_id != admin.institution_id
    ):
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.patch("/departments/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DepartmentRead:
    dept = _get_dept_scoped(department_id, db, admin)
    return crud.update_department(db, dept, payload)
