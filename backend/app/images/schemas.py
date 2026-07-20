import uuid
from datetime import datetime

from pydantic import BaseModel

from app.images.models import ImageStatus


class ImageRead(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    width: int | None
    height: int | None
    uploaded_at: datetime
    taken_at: datetime | None
    camera: str | None
    lens: str | None
    gps: str | None
    status: ImageStatus
    url: str
    thumbnail_url: str | None


class ImageList(BaseModel):
    items: list[ImageRead]
    total: int
    limit: int
    offset: int


class ImageStats(BaseModel):
    count: int
    storage_bytes: int
