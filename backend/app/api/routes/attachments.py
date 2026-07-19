from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.roles import ADMIN_ROLES
from app.core.storage import storage
from app.crud import attachment as crud
from app.crud import consultation as crud_consultation
from app.models.attachment import Attachment
from app.models.entities import User
from app.schemas.attachment import AttachmentRead

router = APIRouter(tags=["attachments"])


def _scoped_consultation(consultation_id: int, db: Session, user: User):
    c = crud_consultation.get_consultation(db, consultation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if user.institution_id is not None and c.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return c


def _scoped_attachment(
    attachment_id: int, db: Session, user: User
) -> Attachment:
    att = crud.get_attachment(db, attachment_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if user.institution_id is not None and att.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return att


@router.post(
    "/consultations/{consultation_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    consultation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentRead:
    consultation = _scoped_consultation(consultation_id, db, current_user)

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit",
        )

    key = storage.new_key(file.filename or "file")
    storage.save(key, data)

    return crud.create_attachment(
        db,
        consultation_id=consultation.id,
        institution_id=consultation.institution_id,
        uploaded_by_user_id=current_user.id,
        filename=file.filename or key,
        storage_key=key,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
    )


@router.get(
    "/consultations/{consultation_id}/attachments",
    response_model=list[AttachmentRead],
)
def list_attachments(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttachmentRead]:
    _scoped_consultation(consultation_id, db, current_user)
    return crud.list_for_consultation(db, consultation_id)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    att = _scoped_attachment(attachment_id, db, current_user)
    path = storage.full_path(att.storage_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")
    # filename= forces Content-Disposition: attachment (no inline render), and
    # nosniff stops the browser overriding the stored (client-supplied) type.
    return FileResponse(
        path,
        media_type=att.content_type,
        filename=att.filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.delete(
    "/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    att = _scoped_attachment(attachment_id, db, current_user)
    # Uploader or an admin may delete.
    is_owner = att.uploaded_by_user_id == current_user.id
    if not is_owner and current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the uploader or an admin can delete this attachment",
        )
    storage.delete(att.storage_key)
    crud.delete_attachment(db, att)
