from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageRead(BaseModel):
    id: int
    consultation_id: int
    sender_user_id: int
    sender_name: str
    body: str
    created_at: datetime
