from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Department, Institution
from app.schemas.org import (
    DepartmentCreate,
    DepartmentUpdate,
    InstitutionCreate,
    InstitutionUpdate,
)


def institution_read(inst: Institution) -> dict:
    return {
        "id": inst.id,
        "name": inst.name,
        "code": inst.code,
        "motto": inst.motto,
        "address": inst.address,
        "phone": inst.phone,
        "email": inst.email,
        "website": inst.website,
        "primary_color": inst.primary_color,
        "has_logo": bool(inst.logo_key),
        "has_watermark": bool(inst.watermark_key),
        "created_at": inst.created_at,
    }


def update_institution(
    db: Session, inst: Institution, payload: InstitutionUpdate
) -> Institution:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(inst, field, value)
    db.commit()
    db.refresh(inst)
    return inst


# ---- Institutions ----

def list_institutions(db: Session) -> list[Institution]:
    return list(db.scalars(select(Institution).order_by(Institution.name)))


def get_institution(db: Session, institution_id: int) -> Institution | None:
    return db.get(Institution, institution_id)


def get_institution_by_code(db: Session, code: str) -> Institution | None:
    return db.scalar(select(Institution).where(Institution.code == code))


def create_institution(
    db: Session, payload: InstitutionCreate
) -> Institution:
    inst = Institution(name=payload.name, code=payload.code)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


# ---- Departments ----

def list_departments(
    db: Session, *, institution_id: int | None = None
) -> list[Department]:
    stmt = select(Department).order_by(Department.name)
    if institution_id is not None:
        stmt = stmt.where(Department.institution_id == institution_id)
    return list(db.scalars(stmt))


def get_department(db: Session, department_id: int) -> Department | None:
    return db.get(Department, department_id)


def create_department(
    db: Session, payload: DepartmentCreate, *, institution_id: int
) -> Department:
    dept = Department(
        institution_id=institution_id,
        name=payload.name,
        specialty=payload.specialty,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def update_department(
    db: Session, department: Department, payload: DepartmentUpdate
) -> Department:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(department, field, value)
    db.commit()
    db.refresh(department)
    return department
