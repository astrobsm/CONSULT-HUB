from __future__ import annotations

import mimetypes

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    assert_can_manage_institution,
    get_current_user,
    require_admin,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.roles import SUPER_ADMIN
from app.core.storage import storage
from app.crud import org as crud
from app.models.entities import Department, Institution, User
from app.schemas.org import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    InstitutionCreate,
    InstitutionRead,
    InstitutionUpdate,
)

router = APIRouter(tags=["org"])


def _scoped_institution(
    institution_id: int, db: Session, user: User
) -> Institution:
    inst = crud.get_institution(db, institution_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    if user.role != SUPER_ADMIN and user.institution_id != inst.id:
        raise HTTPException(status_code=404, detail="Institution not found")
    return inst


# ---- Institutions ----

@router.get("/institutions", response_model=list[InstitutionRead])
def list_institutions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InstitutionRead]:
    # Super admins see all; everyone else sees only their own institution.
    if current_user.role == SUPER_ADMIN:
        return [crud.institution_read(i) for i in crud.list_institutions(db)]
    if current_user.institution_id is None:
        return []
    inst = crud.get_institution(db, current_user.institution_id)
    return [crud.institution_read(inst)] if inst else []


@router.get("/institutions/{institution_id}", response_model=InstitutionRead)
def get_institution(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionRead:
    return crud.institution_read(
        _scoped_institution(institution_id, db, current_user)
    )


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
    return crud.institution_read(crud.create_institution(db, payload))


@router.patch(
    "/institutions/{institution_id}", response_model=InstitutionRead
)
def update_institution(
    institution_id: int,
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> InstitutionRead:
    inst = _scoped_institution(institution_id, db, admin)
    return crud.institution_read(crud.update_institution(db, inst, payload))


def _upload_brand_image(
    inst: Institution, file: UploadFile, kind: str, db: Session
) -> None:
    data = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=422, detail="Must be an image")
    key = storage.new_key(file.filename or f"{kind}.png")
    storage.save(key, data)
    if kind == "logo":
        if inst.logo_key:
            storage.delete(inst.logo_key)
        inst.logo_key = key
    else:
        if inst.watermark_key:
            storage.delete(inst.watermark_key)
        inst.watermark_key = key
    db.commit()


@router.post(
    "/institutions/{institution_id}/logo", response_model=InstitutionRead
)
def upload_logo(
    institution_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> InstitutionRead:
    inst = _scoped_institution(institution_id, db, admin)
    _upload_brand_image(inst, file, "logo", db)
    return crud.institution_read(inst)


@router.post(
    "/institutions/{institution_id}/watermark",
    response_model=InstitutionRead,
)
def upload_watermark(
    institution_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> InstitutionRead:
    inst = _scoped_institution(institution_id, db, admin)
    _upload_brand_image(inst, file, "watermark", db)
    return crud.institution_read(inst)


@router.get("/institutions/{institution_id}/logo")
def get_logo(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    inst = _scoped_institution(institution_id, db, current_user)
    if not inst.logo_key:
        raise HTTPException(status_code=404, detail="No logo")
    path = storage.full_path(inst.logo_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Logo missing")
    media = mimetypes.guess_type(inst.logo_key)[0] or "image/png"
    return FileResponse(path, media_type=media)


@router.get("/institutions/{institution_id}/watermark")
def get_watermark(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    inst = _scoped_institution(institution_id, db, current_user)
    if not inst.watermark_key:
        raise HTTPException(status_code=404, detail="No watermark")
    path = storage.full_path(inst.watermark_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Watermark missing")
    media = mimetypes.guess_type(inst.watermark_key)[0] or "image/png"
    return FileResponse(path, media_type=media)


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
