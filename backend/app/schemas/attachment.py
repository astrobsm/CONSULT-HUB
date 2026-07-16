from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consultation_id: int
    uploaded_by_user_id: int | None
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
